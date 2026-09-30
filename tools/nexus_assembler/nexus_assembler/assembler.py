from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import VERSION
from .data import canonical, deep_merge, dump_yaml, load_yaml, transform
from .errors import Error, PolicyError, ValidationError
from .repository_declarations import validate as validate_repository_declarations


@dataclass(slots=True)
class Result:
    blueprint: dict[str, Any]
    components: list[dict[str, Any]]
    compose: dict[str, Any]
    lock: dict[str, Any]
    build_plan: dict[str, Any]
    environment_example: str
    runtime_files: dict[str, str]
    secrets_required: str
    policy_report: dict[str, Any]
    readme: str


class Repository:
    def __init__(self, root: str | Path | None = None) -> None:
        if root is None:
            root = os.environ.get("NEXUS_ROOT") or Path.cwd()
        self.root = Path(root).resolve()
        self.composition_root = self.root / "composition"
        self._catalog: dict[str, dict[str, dict[str, Any]]] | None = None

    def load_dimension(self, directory: str, dimension_id: str) -> dict[str, Any]:
        path = self.composition_root / directory / f"{dimension_id}.yaml"
        if not path.is_file():
            singular = directory[:-1] if directory.endswith("s") else directory
            raise ValidationError(f"unknown {singular} {dimension_id!r}")
        value = load_yaml(path)
        if not isinstance(value, dict):
            raise ValidationError(f"{path} must contain a mapping")
        return value

    @property
    def catalog(self) -> dict[str, dict[str, dict[str, Any]]]:
        if self._catalog is not None:
            return self._catalog
        index: dict[str, dict[str, dict[str, Any]]] = {}
        for path in sorted((self.composition_root / "catalog").glob("*.yaml")):
            entry = load_yaml(path)
            if not isinstance(entry, dict):
                raise ValidationError(f"{path} must contain a mapping")
            self._validate_catalog_entry(entry, path)
            entry = {**entry, "_path": str(path)}
            capability = entry["capability"]
            implementation = entry["implementation"]
            bucket = index.setdefault(capability, {})
            if implementation in bucket:
                raise ValidationError(f"duplicate catalog implementation {capability}/{implementation}")
            bucket[implementation] = entry
        self._catalog = index
        return index

    def dimensions(self, directory: str) -> list[str]:
        return [load_yaml(path)["id"] for path in sorted((self.composition_root / directory).glob("*.yaml"))]

    def _validate_catalog_entry(self, entry: dict[str, Any], path: Path) -> None:
        required = {
            "apiVersion", "kind", "capability", "implementation", "type",
            "fragment", "dependencies", "services", "artifacts",
        }
        missing = sorted(required - set(entry))
        if missing:
            raise ValidationError(f"{path} is missing {', '.join(missing)}")
        if entry["apiVersion"] != "nexus.io/component/v1alpha1" or entry["kind"] != "ComponentImplementation":
            raise ValidationError(f"{path} is not a supported component catalog entry")
        fragment = self.root / entry["fragment"]
        if not fragment.is_file():
            raise ValidationError(f"catalog fragment does not exist: {fragment}")


class Assembler:
    def __init__(self, repository: Repository | None = None) -> None:
        self.repository = repository or Repository()

    def assemble(self, blueprint_or_path: str | Path | dict[str, Any]) -> Result:
        if isinstance(blueprint_or_path, (str, Path)):
            blueprint = load_yaml(blueprint_or_path)
        else:
            blueprint = canonical(blueprint_or_path)
        context = self._validate_blueprint(blueprint)
        components = self._resolve_components(blueprint, context["edition"])
        compose = self._assemble_compose(blueprint, components)
        artifacts = self._apply_deployment_policy(compose, blueprint, components, context)
        environment_example = self._render_environment_example(blueprint, components, artifacts, context)
        runtime_files = self._render_runtime_files(blueprint, components)
        secrets_required = self._render_secrets_required(components)
        build_plan = self._build_plan(blueprint, components, artifacts, context)
        lock = self._lock_file(blueprint, components, artifacts)
        policy_report = self._evaluate_policies(blueprint, components, compose, artifacts, context)
        return Result(
            blueprint=blueprint,
            components=components,
            compose=compose,
            lock=lock,
            build_plan=build_plan,
            environment_example=environment_example,
            runtime_files=runtime_files,
            secrets_required=secrets_required,
            policy_report=policy_report,
            readme=self._render_readme(blueprint, components, policy_report),
        )

    def write_deployment_package(self, result: Result, output_directory: str | Path, force: bool = False) -> Path:
        destination = Path(output_directory).resolve()
        if destination.exists() and not destination.is_dir():
            raise Error(f"output path is not a directory: {destination}")
        if destination.exists() and any(destination.iterdir()) and not force:
            raise Error(f"deployment package directory is not empty: {destination}; pass --force to replace it")
        destination.parent.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix=f".{destination.name}.tmp-", dir=destination.parent))
        backup: Path | None = None
        try:
            self._write_package(result, staging, destination)
            if destination.exists():
                backup = destination.with_name(f"{destination.name}.previous-{os.getpid()}-{os.urandom(6).hex()}")
                destination.rename(backup)
            staging.rename(destination)
            if backup:
                shutil.rmtree(backup, ignore_errors=True)
        except Exception:
            if backup and backup.exists() and not destination.exists():
                backup.rename(destination)
            raise
        finally:
            if staging.exists():
                shutil.rmtree(staging, ignore_errors=True)
        return destination

    def _write_package(self, result: Result, directory: Path, reference_destination: Path) -> None:
        compose = self._compose_for_output(result.compose, result.blueprint, reference_destination)
        files = {
            "compose.yml": dump_yaml(compose),
            "blueprint.yaml": dump_yaml(result.blueprint),
            "compose.lock.yaml": dump_yaml(result.lock),
            "build-plan.yaml": dump_yaml(result.build_plan),
            ".env.example": result.environment_example,
            "secrets.required": result.secrets_required,
            "policy-report.json": json.dumps(canonical(result.policy_report), indent=2) + "\n",
            "README.md": result.readme,
        }
        for name, content in files.items():
            self._atomic_write(directory / name, content)
        for name, content in result.runtime_files.items():
            self._atomic_write(directory / "runtime" / name, content)
        if result.blueprint.get("deployment", {}).get("environment") == "production":
            self._copy_production_assets(directory, result.components)

    def validate_deployment_package(self, path: str | Path) -> dict[str, Any]:
        path = Path(path)
        directory = path.resolve() if path.is_dir() else None
        package_result = self._validate_package(directory) if directory else {"status": "not-applicable"}
        compose_path = directory / "compose.yml" if directory else path
        if not compose_path.is_file():
            raise ValidationError(f"Compose file not found: {compose_path}")
        compose = load_yaml(compose_path)
        self._validate_compose_structure(compose)
        required_variables = sorted(set(re.findall(r"\$\{([A-Z][A-Z0-9_]*):\?", compose_path.read_text())))
        docker_result = self._validate_with_docker(compose_path, required_variables)
        return {
            "status": "passed",
            "compose": str(compose_path),
            "services": sorted(compose["services"]),
            "requiredVariables": required_variables,
            "dockerCompose": docker_result,
            "package": package_result,
        }

    def plan(self, blueprint_or_path: str | Path | dict[str, Any]) -> dict[str, Any]:
        result = self.assemble(blueprint_or_path)
        return {
            "product": result.blueprint.get("product", {}).get("name"),
            "edition": result.blueprint.get("product", {}).get("edition"),
            "deployment": result.blueprint["deployment"],
            "repositories": validate_repository_declarations(result.blueprint.get("repositories")),
            "components": [
                {
                    "capability": component["capability"],
                    "implementation": component["implementation"],
                    "services": component["services"],
                }
                for component in result.components
            ],
            "artifacts": result.lock["artifacts"],
            "policyStatus": result.policy_report["status"],
        }

    def collect_secrets(self, blueprint_or_path: str | Path | dict[str, Any], output_path: str | Path) -> dict[str, Any]:
        components = self.assemble(blueprint_or_path).components
        env_files: list[str] = []
        for component in components:
            for relative_path in component.get("secretsEnvFiles", []) or []:
                if (self.repository.root / relative_path).is_file() and relative_path not in env_files:
                    env_files.append(relative_path)
        if not env_files:
            raise ValidationError("no .env files found for the selected components")

        key_sources: dict[str, list[str]] = {}
        key_re = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=")
        for relative_path in env_files:
            for line in (self.repository.root / relative_path).read_text().splitlines():
                text = re.sub(r"^\s*", "", line)
                text = re.sub(r"^export\s+", "", text)
                match = key_re.match(text)
                if match:
                    key_sources.setdefault(match.group(1), []).append(relative_path)
        duplicates = {key: sources for key, sources in key_sources.items() if len(sources) > 1}
        if duplicates:
            details = "; ".join(f"{key}: {', '.join(dict.fromkeys(sources))}" for key, sources in duplicates.items())
            raise ValidationError(f"duplicate secret keys across .env files: {details}")

        lines = [
            f"# Generated by Nexus Assembler {VERSION}.",
            "# Regenerate this file after changing a service-level .env file.",
        ]
        for relative_path in env_files:
            lines += ["", f"# Source: {relative_path}", (self.repository.root / relative_path).read_text().rstrip()]
        destination = Path(output_path).resolve()
        self._atomic_write(destination, "\n".join(lines) + "\n", mode=0o600)
        required_names = sorted({name for component in components for name in component.get("secrets", {})})
        return {
            "output": str(destination),
            "envFiles": env_files,
            "missingRequired": sorted(set(required_names) - set(key_sources)),
        }

    def _validate_blueprint(self, blueprint: Any) -> dict[str, Any]:
        if not isinstance(blueprint, dict):
            raise ValidationError("blueprint must be a mapping")
        self._reject_unknown_keys(blueprint, {"apiVersion", "product", "deployment", "registry", "capabilities", "repositories"}, "blueprint")
        if blueprint.get("apiVersion") != "nexus.io/composition/v1alpha1":
            raise ValidationError("apiVersion must be nexus.io/composition/v1alpha1")
        product = blueprint.get("product")
        deployment = blueprint.get("deployment")
        if not isinstance(product, dict):
            raise ValidationError("product must be a mapping")
        if not isinstance(deployment, dict):
            raise ValidationError("deployment must be a mapping")
        if "registry" in blueprint and not isinstance(blueprint["registry"], dict):
            raise ValidationError("registry must be a mapping")
        if "capabilities" in blueprint and not isinstance(blueprint["capabilities"], dict):
            raise ValidationError("capabilities must be a mapping")
        validate_repository_declarations(blueprint.get("repositories"))
        self._reject_unknown_keys(product, {"name", "edition", "description"}, "product")
        self._reject_unknown_keys(deployment, {"target", "environment", "assurance"}, "deployment")
        if isinstance(blueprint.get("registry"), dict):
            self._reject_unknown_keys(blueprint["registry"], {"host", "namespace", "policy"}, "registry")
        name = str(product.get("name", ""))
        if not re.fullmatch(r"[a-z][a-z0-9-]{1,62}", name):
            raise ValidationError("product.name must be a lowercase DNS-style name")
        try:
            edition = self.repository.load_dimension("editions", product["edition"])
            environment = self.repository.load_dimension("environments", deployment["environment"])
            target = self.repository.load_dimension("targets", deployment["target"])
            assurance = self.repository.load_dimension("assurance", deployment["assurance"])
        except KeyError as exc:
            raise ValidationError(f"missing required blueprint field {exc.args[0]!r}") from exc
        if deployment["environment"] not in target.get("allowedEnvironments", []):
            raise ValidationError(f"{deployment['target']} does not support {deployment['environment']}")
        if deployment["assurance"] == "high-assurance" and not (
            deployment["target"] == "self-hosted" and deployment["environment"] == "production"
        ):
            raise ValidationError("high-assurance requires self-hosted production")
        registry_required = str(assurance.get("privateRegistry", "optional")).startswith("required") or deployment["environment"] in target.get("registryRequiredIn", [])
        registry = blueprint.get("registry") or {}
        if registry_required and not str(registry.get("host", "")).strip():
            raise ValidationError("registry.host is required for this target or assurance profile")
        if registry_required and not str(registry.get("namespace", "")).strip():
            raise ValidationError("registry.namespace is required for this target or assurance profile")
        if assurance.get("privateRegistry") == "required-exclusive" and registry.get("policy") != "private-only":
            raise ValidationError("high-assurance requires registry.policy private-only")
        return {
            "edition": edition,
            "environment": environment,
            "target": target,
            "assurance": assurance,
            "registry_required": registry_required,
        }

    @staticmethod
    def _reject_unknown_keys(mapping: dict[str, Any], allowed: set[str], label: str) -> None:
        unknown = sorted(set(map(str, mapping)) - allowed)
        if unknown:
            raise ValidationError(f"unknown {label} fields: {', '.join(unknown)}")

    def _resolve_components(self, blueprint: dict[str, Any], edition: dict[str, Any]) -> list[dict[str, Any]]:
        choices = canonical(edition.get("defaults", {}))
        overrides = blueprint.get("capabilities", {}) or {}
        if not isinstance(overrides, dict):
            raise ValidationError("capabilities must be a mapping")
        for capability, value in overrides.items():
            implementation, enabled = self._normalize_capability_choice(value)
            if enabled:
                choices[capability] = implementation
            else:
                choices.pop(capability, None)
        missing = [cap for cap in edition.get("required", []) if cap not in choices]
        if missing:
            raise ValidationError(f"edition requires capabilities: {', '.join(missing)}")
        disallowed = sorted(set(choices) - set(edition.get("allowed", [])))
        if disallowed:
            raise ValidationError(f"edition does not allow capabilities: {', '.join(disallowed)}")
        resolved: dict[str, dict[str, Any]] = {}
        visiting: set[str] = set()

        def resolve(capability: str, implementation: str) -> None:
            if capability in resolved:
                return
            if capability in visiting:
                raise ValidationError(f"cyclic dependency involving {capability}")
            implementations = self.repository.catalog.get(capability)
            if not implementations or implementation not in implementations:
                available = ", ".join(sorted(implementations or {})) or "none"
                raise ValidationError(f"unknown implementation {capability}/{implementation}; available: {available}")
            visiting.add(capability)
            component = implementations[implementation]
            entitlement = component.get("entitlement")
            if entitlement and entitlement not in edition.get("entitlements", []):
                raise ValidationError(f"{capability}/{implementation} requires edition entitlement {entitlement}")
            for dependency in component.get("dependencies", []):
                dep_impl = choices.get(dependency) or edition.get("defaults", {}).get(dependency)
                if dep_impl is None:
                    candidates = self.repository.catalog.get(dependency, {})
                    if len(candidates) == 1:
                        dep_impl = next(iter(candidates))
                if dep_impl is None:
                    raise ValidationError(f"{capability} requires unselected capability {dependency}")
                choices.setdefault(dependency, dep_impl)
                resolve(dependency, dep_impl)
            visiting.remove(capability)
            resolved[capability] = component

        for capability in sorted(list(choices)):
            resolve(capability, choices[capability])
        return [resolved[key] for key in sorted(resolved)]

    @staticmethod
    def _normalize_capability_choice(value: Any) -> tuple[str, bool]:
        if isinstance(value, str):
            return value, value != "disabled"
        if not isinstance(value, dict) or not isinstance(value.get("implementation"), str):
            raise ValidationError("capability choice must be an implementation string or mapping")
        return value["implementation"], value.get("enabled", True)

    def _assemble_compose(self, blueprint: dict[str, Any], components: list[dict[str, Any]]) -> dict[str, Any]:
        compose = load_yaml(self.repository.composition_root / "base.compose.yml")
        for component in components:
            fragment = load_yaml(self.repository.root / component["fragment"])
            compose = deep_merge(compose, fragment)
        product_name = blueprint["product"]["name"]
        compose["name"] = f"{product_name}-{blueprint['deployment']['environment']}"
        compose["networks"]["system"]["name"] = f"{product_name}-system"
        self._validate_compose_structure(compose)
        return compose

    def _apply_deployment_policy(self, compose: dict[str, Any], blueprint: dict[str, Any], components: list[dict[str, Any]], context: dict[str, Any]) -> list[dict[str, Any]]:
        environment_id = blueprint["deployment"]["environment"]
        assurance_id = blueprint["deployment"]["assurance"]
        production = environment_id == "production"
        hardened = assurance_id in {"hardened", "high-assurance"}

        artifact_index: dict[str, dict[str, Any]] = {}
        for component in components:
            for service, artifact in component.get("artifacts", {}).items():
                artifact_index[service] = {
                    **artifact,
                    "capability": component["capability"],
                    "implementation": component["implementation"],
                }

        artifacts: list[dict[str, Any]] = []
        required_names = self._required_variable_names(components)
        for service_name, service in compose["services"].items():
            service["restart"] = context["environment"].get("restartPolicy", "unless-stopped")
            artifact = artifact_index.get(service_name)

            if production or hardened:
                if not artifact:
                    raise ValidationError(f"missing artifact policy for service {service_name}")
                service.pop("build", None)
                service["image"] = self._deployment_image(blueprint, artifact)
                service["pull_policy"] = "always"

            if production:
                if "env_file" in service:
                    service["env_file"] = ["${AUTH_ENV_FILE:?AUTH_ENV_FILE is required}"]
                transformed = self._require_variables(service, required_names)
                service.clear()
                service.update(transformed)

            if hardened:
                service["security_opt"] = sorted(
                    set((service.get("security_opt") or []) + ["no-new-privileges:true"])
                )
                service["privileged"] = False

            if artifact:
                artifacts.append(self._artifact_record(service_name, service, artifact))

        if assurance_id == "high-assurance":
            compose["networks"]["system"]["internal"] = True

        if production:
            self._prepare_production_mounts(compose, components)
            self._prepare_production_gateway(compose, components)

        return sorted(artifacts, key=lambda item: item["service"])

    @staticmethod
    def _deployment_image(blueprint: dict[str, Any], artifact: dict[str, Any]) -> str:
        registry = blueprint["registry"]
        host = registry["host"].rstrip("/")
        namespace = registry["namespace"].strip("/")
        digest_variable = artifact["digestVariable"]
        return f"{host}/{namespace}/{artifact['repository']}@${{{digest_variable}:?{digest_variable} is required}}"

    @staticmethod
    def _required_variable_names(components: list[dict[str, Any]]) -> list[str]:
        names: set[str] = set()
        for component in components:
            names.update(component.get("secrets", {}))
            for name, definition in component.get("configuration", {}).items():
                if definition.get("productionRequired"):
                    names.add(name)
        if any(component["capability"] == "authentication" for component in components):
            names.add("AUTH_ENV_FILE")
        return sorted(names)

    @staticmethod
    def _require_variables(value: Any, names: list[str]) -> Any:
        def replace(item: Any) -> Any:
            if not isinstance(item, str):
                return item
            text = item
            for name in names:
                text = re.sub(rf"\$\{{{re.escape(name)}:-[^}}]*\}}", f"${{{name}:?{name} is required}}", text)
            return text
        return transform(value, replace)

    @staticmethod
    def _artifact_record(service_name: str, service: dict[str, Any], artifact: dict[str, Any]) -> dict[str, Any]:
        record = {
            "service": service_name,
            "capability": artifact["capability"],
            "implementation": artifact["implementation"],
            "mode": artifact["mode"],
            "source": artifact.get("source"),
            "upstream": artifact.get("upstream"),
            "repository": artifact["repository"],
            "digestVariable": artifact["digestVariable"],
            "deploymentImage": service.get("image"),
            "digestResolved": bool(re.search(r"@sha256:[a-f0-9]{64}$", str(service.get("image", "")))),
            "runtimeBuild": "build" in service,
        }
        return {k: v for k, v in record.items() if v is not None}

    def _render_environment_example(self, blueprint, components, artifacts, context) -> str:
        development = blueprint["deployment"]["environment"] == "development"
        lines = [
            f"# Generated by Nexus Assembler {VERSION}; values are examples, never secrets.",
            "# Copy to a private environment file and replace every required value.", "",
        ]
        configuration: dict[str, Any] = {}
        for component in components:
            for name, value in component.get("configuration", {}).items():
                configuration.setdefault(name, value)
        if any(component["capability"] == "authentication" for component in components):
            configuration.setdefault("AUTH_ENV_FILE", {"description": "Absolute path to Keycloak and PostgreSQL runtime environment values", "productionRequired": True})
        for name in sorted(configuration):
            definition = configuration[name]
            if definition.get("scope") == "authentication-env":
                continue
            if definition.get("description"):
                lines.append(f"# {definition['description']}")
            lines += [f"{name}={definition.get('developmentDefault', '') if development else ''}", ""]
        secrets: dict[str, Any] = {}
        for component in components:
            for name, value in component.get("secrets", {}).items():
                secrets.setdefault(name, value)
        if secrets:
            lines.append("# Secrets: supply through the selected external secret workflow.")
            for name in sorted(secrets):
                if secrets[name].get("scope") == "authentication-env":
                    continue
                if secrets[name].get("description"):
                    lines.append(f"# {secrets[name]['description']}")
                lines.append(f"{name}=")
            lines.append("")
        if context["registry_required"]:
            lines.append("# Immutable artifact digests produced by the approved build or mirror pipeline.")
            for name in sorted({artifact["digestVariable"] for artifact in artifacts}):
                lines.append(f"{name}=")
            lines.append("")
        return "\n".join(lines)

    @staticmethod
    def _render_runtime_files(blueprint, components) -> dict[str, str]:
        if not any(component["capability"] == "authentication" for component in components):
            return {}
        production = blueprint["deployment"]["environment"] == "production"
        hostname = "" if production else "auth.localhost"
        lines = [
            "# Generated authentication runtime environment contract.",
            "# Copy to a private file, replace blank secrets, and set AUTH_ENV_FILE",
            "# in the root Compose interpolation environment to its absolute path.",
            "KC_DB=postgres", "KC_DB_URL_HOST=keycloak-db", "KC_DB_URL_PORT=5432", "KC_DB_URL_DATABASE=keycloak",
            "KC_DB_USERNAME=keycloak", "KC_DB_PASSWORD=", "KC_DB_POOL_MIN_SIZE=10", "KC_DB_POOL_MAX_SIZE=50",
            f"KC_HOSTNAME={hostname}", f"KC_HOSTNAME_STRICT={'true' if production else 'false'}", "KC_PROXY_HEADERS=xforwarded",
            "KC_HTTP_ENABLED=true", "KC_BOOTSTRAP_ADMIN_USERNAME=", "KC_BOOTSTRAP_ADMIN_PASSWORD=", "POSTGRES_DB=keycloak",
            "POSTGRES_USER=keycloak", "POSTGRES_PASSWORD=", "",
        ]
        return {"auth.env.example": "\n".join(lines)}

    @staticmethod
    def _render_secrets_required(components) -> str:
        secrets: dict[str, Any] = {}
        for component in components:
            for name, definition in component.get("secrets", {}).items():
                secrets.setdefault(name, {**definition, "capabilities": []})
                secrets[name]["capabilities"].append(component["capability"])
        lines = ["# Required runtime secrets; this file contains names only."]
        for name in sorted(secrets):
            definition = secrets[name]
            lines.append(f"{name}\t{','.join(sorted(set(definition['capabilities'])))}\t{definition.get('description', '')}")
        return "\n".join(lines) + "\n"

    @staticmethod
    def _build_plan(blueprint, components, artifacts, context):
        assurance = context["assurance"]
        result_artifacts = []
        for artifact in artifacts:
            actions = ["build"] if artifact["mode"] == "internal-build" else ["resolve-upstream-digest", "verify-upstream", "mirror"]
            actions += ["scan", "generate-sbom", "attest-provenance", "sign", "push"]
            result_artifacts.append({**artifact, "actions": actions})
        return {
            "apiVersion": "nexus.io/build-plan/v1alpha1",
            "product": blueprint["product"]["name"],
            "environment": blueprint["deployment"]["environment"],
            "assurance": blueprint["deployment"]["assurance"],
            "registry": blueprint.get("registry"),
            "requirements": {
                "sbom": bool(assurance.get("requireSbom")),
                "provenance": bool(assurance.get("requireProvenance")),
                "signature": bool(assurance.get("requireSignature")),
                "reproducibleBuild": bool(assurance.get("requireReproducibleBuild")),
            },
            "artifacts": result_artifacts,
        }

    @staticmethod
    def _lock_file(blueprint, components, artifacts):
        blueprint_json = json.dumps(canonical(blueprint), separators=(",", ":"))
        return {
            "apiVersion": "nexus.io/composition-lock/v1alpha1",
            "assembler": {"name": "nexus-assembler", "version": VERSION},
            "blueprintDigest": f"sha256:{hashlib.sha256(blueprint_json.encode()).hexdigest()}",
            "components": [{"capability": c["capability"], "implementation": c["implementation"], "fragment": c["fragment"]} for c in components],
            "artifacts": artifacts,
        }

    def _evaluate_policies(self, blueprint, components, compose, artifacts, context):
        production = blueprint["deployment"]["environment"] == "production"
        hardened = blueprint["deployment"]["assurance"] in {"hardened", "high-assurance"}
        registry_host = (blueprint.get("registry") or {}).get("host")
        services = compose["services"]
        private_services = {name for c in components for name in c.get("security", {}).get("privateServices", [])}
        checks = []
        self._add_check(checks, "unique-services", True, True, "service names are unique after dependency resolution")
        self._add_check(checks, "runtime-builds-forbidden", not production or all("build" not in s for s in services.values()), production, "production Compose contains no build instructions")
        self._add_check(checks, "immutable-images", not hardened or all("@${" in str(a.get("deploymentImage", "")) for a in artifacts), hardened, "hardened artifacts are selected by required digest variables")
        self._add_check(checks, "private-registry-only", not hardened or all(str(a.get("deploymentImage", "")).startswith(f"{registry_host}/") for a in artifacts), hardened, "hardened runtime images resolve through the selected private registry")
        self._add_check(checks, "no-development-secret-defaults", not production or "change-me" not in dump_yaml(compose), production, "production output contains no change-me secret defaults")
        self._add_check(checks, "privileged-forbidden", not hardened or all(s.get("privileged") is not True for s in services.values()), hardened, "hardened services are not privileged")
        self._add_check(checks, "private-ports-forbidden", all("ports" not in services.get(name, {}) for name in private_services), True, "private dependencies publish no host ports")
        self._add_check(checks, "no-new-privileges", not hardened or all("no-new-privileges:true" in (s.get("security_opt") or []) for s in services.values()), hardened, "hardened services deny privilege escalation")
        gateway = services.get("gateway", {})
        tls_configured = gateway.get("environment", {}).get("GATEWAY_TLS_REDIRECT") == "1" and "${GATEWAY_HTTPS_PORT:-443}:443" in (gateway.get("ports") or []) and any("/etc/nginx/ssl:ro" in str(m) for m in gateway.get("volumes") or [])
        self._add_check(checks, "production-tls", not production or tls_configured, production, "production gateway redirects to HTTPS and requires mounted certificate material")
        selected = {c["capability"] for c in components}
        warnings = [{"id": f"dormant-gateway-route-{cap}", "message": f"the current gateway image contains a route template for unselected capability {cap}; requests fail closed with no upstream"} for cap in ["website", "authentication", "service-status", "observability"] if cap not in selected]
        if blueprint["deployment"]["assurance"] == "high-assurance":
            warnings.append({"id": "host-controls-outside-compose", "message": "host hardening, signature admission, external secret injection, encrypted backup, and external audit require deployment-platform enforcement"})
        failures = [check for check in checks if check["required"] and check["status"] != "passed"]
        return {"apiVersion": "nexus.io/policy-report/v1alpha1", "status": "passed" if not failures else "failed", "product": blueprint["product"]["name"], "deployment": blueprint["deployment"], "checks": checks, "warnings": warnings, "failures": [f["id"] for f in failures]}

    @staticmethod
    def _add_check(checks, check_id, passed, required, message):
        checks.append({"id": check_id, "status": "passed" if passed else "failed", "required": bool(required), "message": message})

    @staticmethod
    def _render_readme(blueprint, components, policy_report):
        deployment = blueprint["deployment"]
        capability_lines = "\n".join(f"- `{c['capability']}` using `{c['implementation']}`" for c in components)
        if deployment["environment"] == "production":
            required_hint = "Populate `.env.example`, copy `runtime/auth.env.example` to a private runtime file, set `AUTH_ENV_FILE` to its absolute path, and resolve every image digest before deployment."
            compose_command = "docker compose --env-file .env -f compose.yml up -d"
        else:
            required_hint = "Copy `.env.example` to `.env` when local overrides are needed."
            compose_command = "docker compose -f compose.yml up -d --build"
        return f"""# {blueprint['product']['name']} Deployment Package

This deployment package was produced by Nexus Assembler {VERSION}. Do not
edit assembled files directly; change the blueprint or catalog and reassemble.

## Blueprint

- Edition: `{blueprint['product']['edition']}`
- Target: `{deployment['target']}`
- Environment: `{deployment['environment']}`
- Assurance: `{deployment['assurance']}`
- Policy status: `{policy_report['status']}`

## Capabilities

{capability_lines}

## Use

{required_hint}

```sh
nexus validate .
{compose_command}
```

Review `policy-report.json`, `compose.lock.yaml`, `build-plan.yaml`, and
`secrets.required` before deployment. A passed Compose policy report does
not replace host, registry, secret-provider, backup, or operational controls.
"""

    @staticmethod
    def _prepare_production_mounts(compose, components):
        for component in components:
            for rewrite in component.get("production", {}).get("volumeRewrites", []) or []:
                service = compose.get("services", {}).get(rewrite["service"])
                if not service:
                    continue
                prefix = rewrite["matchPrefix"]
                volumes = []
                for mount in service.get("volumes", []) or []:
                    text = str(mount)
                    if text.startswith(prefix):
                        if rewrite.get("namedVolume"):
                            named = rewrite["namedVolume"]
                            text = f"{named}:{text[len(prefix):]}"
                            compose.setdefault("volumes", {}).setdefault(named, {})
                        else:
                            text = f"{rewrite['replacement']}{text[len(prefix):]}"
                    volumes.append(text)
                service["volumes"] = volumes

    @staticmethod
    def _prepare_production_gateway(compose, components):
        gateway = compose.get("services", {}).get("gateway")
        if not gateway:
            return
        for component in components:
            production = component.get("production", {}) or {}
            for override in production.get("environmentOverrides", []) or []:
                service = compose.get("services", {}).get(override["service"])
                if service:
                    service.setdefault("environment", {})[override["key"]] = override["value"]
            for mapping in production.get("portMappings", []) or []:
                service = compose.get("services", {}).get(mapping["service"])
                if service:
                    service.setdefault("ports", [])
                    if mapping["mapping"] not in service["ports"]:
                        service["ports"].append(mapping["mapping"])
            for volume in production.get("gatewayVolumes", []) or []:
                gateway.setdefault("volumes", []).append(volume)

    def _compose_for_output(self, compose, blueprint, destination: Path):
        output = copy.deepcopy(compose)
        if blueprint["deployment"]["environment"] != "development":
            return output
        for service in output["services"].values():
            if isinstance(service.get("build"), dict) and isinstance(service["build"].get("context"), str):
                service["build"]["context"] = self._rebase_repository_path(service["build"]["context"], destination)
            if "env_file" in service:
                entries = service.get("env_file") or []
                if not isinstance(entries, list): entries = [entries]
                rebased = []
                for entry in entries:
                    if isinstance(entry, dict) and isinstance(entry.get("path"), str):
                        rebased.append({**entry, "path": self._rebase_repository_path(entry["path"], destination)})
                    elif isinstance(entry, str):
                        rebased.append(self._rebase_repository_path(entry, destination))
                    else:
                        rebased.append(entry)
                service["env_file"] = rebased
            if "volumes" in service:
                service["volumes"] = [self._rebase_bind_mount(mount, destination) for mount in service.get("volumes") or []]
        return output

    def _rebase_repository_path(self, path: str, destination: Path) -> str:
        if not path.startswith("./"):
            return path
        absolute = (self.repository.root / path).resolve()
        return os.path.relpath(absolute, destination)

    def _rebase_bind_mount(self, mount: Any, destination: Path):
        if not isinstance(mount, str) or not mount.startswith("./"):
            return mount
        source, sep, remainder = mount.partition(":")
        rebased = self._rebase_repository_path(source, destination)
        return f"{rebased}:{remainder}" if sep else rebased

    def _copy_production_assets(self, destination: Path, components):
        for component in components:
            for copy_spec in component.get("production", {}).get("assetCopies", []) or []:
                source = self.repository.root / copy_spec["source"]
                if not source.is_dir():
                    continue
                target = destination / copy_spec["destination"]
                target.mkdir(parents=True, exist_ok=True)
                for child in sorted(source.iterdir()):
                    if child.is_dir(): shutil.copytree(child, target / child.name, dirs_exist_ok=True)
                    else: shutil.copy2(child, target / child.name)

    @staticmethod
    def _validate_compose_structure(compose):
        if not isinstance(compose, dict):
            raise ValidationError("Compose document must be a mapping")
        services = compose.get("services")
        if not isinstance(services, dict) or not services:
            raise ValidationError("Compose services must be a non-empty mapping")
        for name, service in services.items():
            if not isinstance(service, dict):
                raise ValidationError(f"service {name} must be a mapping")
            if "image" not in service and "build" not in service:
                raise ValidationError(f"service {name} must declare image or build")
            health_test = service.get("healthcheck", {}).get("test") if isinstance(service.get("healthcheck"), dict) else None
            if health_test is not None and (not isinstance(health_test, list) or any(not isinstance(item, str) for item in health_test)):
                raise ValidationError(f"service {name} healthcheck.test must be a list of strings")
        return True

    def _validate_package(self, directory: Path):
        required = [".env.example", "README.md", "build-plan.yaml", "compose.lock.yaml", "compose.yml", "policy-report.json", "secrets.required"]
        compose_text = (directory / "compose.yml").read_text() if (directory / "compose.yml").is_file() else ""
        if "AUTH_ENV_FILE" in compose_text:
            required.append("runtime/auth.env.example")
        missing = [name for name in required if not (directory / name).is_file()]
        if missing:
            raise ValidationError(f"deployment package is missing: {', '.join(missing)}")
        blueprint_path = directory / "blueprint.yaml"
        if not blueprint_path.is_file():
            raise ValidationError("deployment package is missing: blueprint.yaml")
        blueprint = load_yaml(blueprint_path)
        lock = load_yaml(directory / "compose.lock.yaml")
        try:
            policy = json.loads((directory / "policy-report.json").read_text())
        except json.JSONDecodeError as exc:
            raise ValidationError(f"invalid policy-report.json: {exc}") from exc
        compose = load_yaml(directory / "compose.yml")
        digest_json = json.dumps(canonical(blueprint), separators=(",", ":"))
        expected = f"sha256:{hashlib.sha256(digest_json.encode()).hexdigest()}"
        if lock.get("blueprintDigest") != expected:
            raise ValidationError("blueprint digest does not match compose.lock.yaml")
        if policy.get("status") != "passed":
            raise PolicyError(f"deployment package policy status is {policy.get('status')!r}")
        for artifact in lock.get("artifacts", []) or []:
            service = compose.get("services", {}).get(artifact["service"])
            if not service:
                raise ValidationError(f"locked service is absent: {artifact['service']}")
            if service.get("image") != artifact.get("deploymentImage"):
                raise ValidationError(f"image for {artifact['service']} differs from compose.lock.yaml")
        return {"status": "passed", "blueprintDigest": expected}

    @staticmethod
    def _validate_with_docker(compose_path: Path, required_variables: list[str]):
        if shutil.which("docker") is None:
            return {"status": "skipped", "reason": "docker compose is unavailable"}
        probe = subprocess.run(["docker", "compose", "version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        if probe.returncode != 0:
            return {"status": "skipped", "reason": "docker compose is unavailable"}
        with tempfile.NamedTemporaryFile("w", suffix=".env") as runtime_env, tempfile.NamedTemporaryFile("w", suffix=".env") as interpolation_env:
            runtime_env.write("NEXUS_VALIDATION=1\n"); runtime_env.flush()
            for name in required_variables:
                if name == "AUTH_ENV_FILE": value = runtime_env.name
                elif name.endswith("_IMAGE_DIGEST"): value = "sha256:" + "a" * 64
                elif name.endswith("_DIR"): value = "/tmp/nexus-assembler-validation"
                elif name.endswith("_PORT"): value = "8080"
                else: value = "nexus-validation"
                interpolation_env.write(f"{name}={value}\n")
            interpolation_env.flush()
            result = subprocess.run(["docker", "compose", "--env-file", interpolation_env.name, "-f", str(compose_path), "config", "--quiet"], capture_output=True, text=True, check=False)
            if result.returncode != 0:
                raise ValidationError(f"docker compose config failed: {result.stderr.strip()}")
        return {"status": "passed", "syntheticRequiredValues": bool(required_variables)}

    @staticmethod
    def _atomic_write(path: Path, content: str, mode: int | None = None):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix=path.name, suffix=".tmp", dir=path.parent)
        try:
            if mode is not None:
                os.fchmod(fd, mode)
            with os.fdopen(fd, "w") as handle:
                handle.write(content)
                handle.flush(); os.fsync(handle.fileno())
            os.replace(temp_name, path)
        finally:
            if os.path.exists(temp_name): os.unlink(temp_name)
