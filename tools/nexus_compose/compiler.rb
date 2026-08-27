# frozen_string_literal: true

require "digest"
require "fileutils"
require "json"
require "open3"
require "pathname"
require "securerandom"
require "tempfile"
require "tmpdir"
require "yaml"

module NexusCompose
  VERSION = "0.3.0"

  class Error < StandardError; end
  class ValidationError < Error; end
  class PolicyError < Error; end

  module Data
    module_function

    def load_yaml(path)
      content = File.read(path)
      value = begin
        YAML.safe_load(content, permitted_classes: [], permitted_symbols: [], aliases: true)
      rescue ArgumentError
        YAML.safe_load(content, [], [], true)
      end
      value || {}
    rescue Psych::Exception => e
      raise ValidationError, "invalid YAML in #{path}: #{e.message}"
    end

    def canonical(value)
      case value
      when Hash
        value.keys.map(&:to_s).sort.each_with_object({}) do |key, result|
          original = value.key?(key) ? key : value.keys.find { |candidate| candidate.to_s == key }
          result[key] = canonical(value[original])
        end
      when Array
        value.map { |item| canonical(item) }
      else
        value
      end
    end

    def yaml(value)
      Psych.dump(canonical(value), nil, line_width: -1)
    end

    def deep_merge(left, right, path = [])
      return canonical(right) unless left.is_a?(Hash) && right.is_a?(Hash)

      result = canonical(left)
      right.each do |key, value|
        string_key = key.to_s
        if result.key?(string_key) && path.last == "services"
          raise ValidationError, "duplicate Compose service #{string_key.inspect}"
        elsif result.key?(string_key) && result[string_key].is_a?(Hash) && value.is_a?(Hash)
          result[string_key] = deep_merge(result[string_key], value, path + [string_key])
        else
          result[string_key] = canonical(value)
        end
      end
      result
    end

    def transform(value, &block)
      transformed = case value
                    when Hash
                      value.each_with_object({}) do |(key, item), result|
                        result[key.to_s] = transform(item, &block)
                      end
                    when Array
                      value.map { |item| transform(item, &block) }
                    else
                      value
                    end
      block.call(transformed)
    end
  end

  module RepositoryDeclarations
    ALLOWED_FIELDS = %w[name url path branch required].freeze

    module_function

    def validate(value)
      return [] if value.nil?
      raise ValidationError, "repositories must be a list" unless value.is_a?(Array)

      repositories = value.map.with_index do |candidate, index|
        label = "repositories[#{index}]"
        raise ValidationError, "#{label} must be a mapping" unless candidate.is_a?(Hash)

        repository = Data.canonical(candidate)
        unknown = repository.keys - ALLOWED_FIELDS
        unless unknown.empty?
          raise ValidationError, "unknown #{label} fields: #{unknown.sort.join(', ')}"
        end

        name = repository["name"].to_s
        unless name.match?(/\A[a-z][a-z0-9-]{0,62}\z/)
          raise ValidationError, "#{label}.name must be a lowercase DNS-style name"
        end

        url = repository["url"].to_s.strip
        raise ValidationError, "#{label}.url is required" if url.empty?

        path = repository["path"].to_s
        clean_path = Pathname.new(path).cleanpath.to_s
        unless path == clean_path && !Pathname.new(path).absolute? && path.start_with?("system/") && path != "system/"
          raise ValidationError, "#{label}.path must be a normalized relative path below system/"
        end

        if repository.key?("branch") && repository["branch"].to_s.strip.empty?
          raise ValidationError, "#{label}.branch must not be empty"
        end
        if repository.key?("required") && ![true, false].include?(repository["required"])
          raise ValidationError, "#{label}.required must be true or false"
        end

        repository.merge(
          "name" => name,
          "url" => url,
          "path" => path,
          "required" => repository.fetch("required", true)
        )
      end

      duplicate_names = duplicates(repositories.map { |repository| repository.fetch("name") })
      duplicate_paths = duplicates(repositories.map { |repository| repository.fetch("path") })
      raise ValidationError, "duplicate repository names: #{duplicate_names.join(', ')}" unless duplicate_names.empty?
      raise ValidationError, "duplicate repository paths: #{duplicate_paths.join(', ')}" unless duplicate_paths.empty?

      repositories
    end

    def duplicates(values)
      values.group_by(&:itself).select { |_value, matches| matches.length > 1 }.keys.sort
    end
    private_class_method :duplicates
  end

  class Repository
    attr_reader :root, :composition_root

    def initialize(root = File.expand_path("../..", __dir__))
      @root = File.expand_path(root)
      @composition_root = File.join(@root, "composition")
    end

    def load_dimension(directory, id)
      path = File.join(composition_root, directory, "#{id}.yaml")
      raise ValidationError, "unknown #{directory.sub(/s$/, "")} #{id.inspect}" unless File.file?(path)

      Data.load_yaml(path)
    end

    def catalog
      @catalog ||= begin
        entries = Dir[File.join(composition_root, "catalog", "*.yaml")].sort.map do |path|
          entry = Data.load_yaml(path)
          validate_catalog_entry(entry, path)
          entry.merge("_path" => path)
        end
        entries.each_with_object({}) do |entry, index|
          capability = entry.fetch("capability")
          implementation = entry.fetch("implementation")
          index[capability] ||= {}
          if index[capability].key?(implementation)
            raise ValidationError, "duplicate catalog implementation #{capability}/#{implementation}"
          end
          index[capability][implementation] = entry
        end
      end
    end

    def dimensions(directory)
      Dir[File.join(composition_root, directory, "*.yaml")].sort.map do |path|
        Data.load_yaml(path).fetch("id")
      end
    end

    private

    def validate_catalog_entry(entry, path)
      required = %w[apiVersion kind capability implementation type fragment dependencies services artifacts]
      missing = required.reject { |key| entry.key?(key) }
      raise ValidationError, "#{path} is missing #{missing.join(', ')}" unless missing.empty?
      unless entry["apiVersion"] == "nexus.io/component/v1alpha1" && entry["kind"] == "ComponentImplementation"
        raise ValidationError, "#{path} is not a supported component catalog entry"
      end
      fragment = File.join(root, entry.fetch("fragment"))
      raise ValidationError, "catalog fragment does not exist: #{fragment}" unless File.file?(fragment)
    end
  end

  Result = Struct.new(
    :blueprint,
    :components,
    :compose,
    :lock,
    :build_plan,
    :environment_example,
    :runtime_files,
    :secrets_required,
    :policy_report,
    :readme,
    keyword_init: true
  ) do
    # Legacy public name retained for API compatibility.
    def selection
      blueprint
    end
  end

  class Assembler
    attr_reader :repository

    def initialize(repository = Repository.new)
      @repository = repository
    end

    def assemble(selection_or_path)
      selection = selection_or_path.is_a?(String) ? Data.load_yaml(selection_or_path) : Data.canonical(selection_or_path)
      context = validate_selection(selection)
      components = resolve_components(selection, context.fetch(:edition))
      compose = assemble_compose(selection, components)
      artifacts = apply_deployment_policy!(compose, selection, components, context)
      environment_example = render_environment_example(selection, components, artifacts, context)
      runtime_files = render_runtime_files(selection, components)
      secrets_required = render_secrets_required(components)
      build_plan = build_plan(selection, components, artifacts, context)
      lock = lock_file(selection, components, artifacts)
      policy_report = evaluate_policies(selection, components, compose, artifacts, context)

      Result.new(
        blueprint: selection,
        components: components,
        compose: compose,
        lock: lock,
        build_plan: build_plan,
        environment_example: environment_example,
        runtime_files: runtime_files,
        secrets_required: secrets_required,
        policy_report: policy_report,
        readme: render_readme(selection, components, policy_report)
      )
    end

    # Legacy API verb retained for integrations using the former compiler name.
    alias compile assemble

    def write(result, output_directory, force: false)
      destination = File.expand_path(output_directory)
      if File.exist?(destination) && !File.directory?(destination)
        raise Error, "output path is not a directory: #{destination}"
      end
      if File.exist?(destination) && Dir.children(destination).any? && !force
        raise Error, "deployment package directory is not empty: #{destination}; pass --force to replace it"
      end

      parent = File.dirname(destination)
      FileUtils.mkdir_p(parent)
      staging = Dir.mktmpdir(".#{File.basename(destination)}.tmp-", parent)
      backup = nil
      begin
        write_package(result, staging, destination)
        if File.exist?(destination)
          backup = "#{destination}.previous-#{Process.pid}-#{SecureRandom.hex(6)}"
          File.rename(destination, backup)
        end
        File.rename(staging, destination)
        FileUtils.rm_rf(backup) if backup
      rescue StandardError
        File.rename(backup, destination) if backup && File.exist?(backup) && !File.exist?(destination)
        raise
      ensure
        FileUtils.rm_rf(staging) if File.exist?(staging)
      end
      destination
    end

    alias write_deployment_package write

    def write_package(result, directory, reference_destination)
      compose = compose_for_output(result.compose, result.selection, reference_destination)
      files = {
        "compose.yml" => Data.yaml(compose),
        "blueprint.yaml" => Data.yaml(result.selection),
        "compose.lock.yaml" => Data.yaml(result.lock),
        "build-plan.yaml" => Data.yaml(result.build_plan),
        ".env.example" => result.environment_example,
        "secrets.required" => result.secrets_required,
        "policy-report.json" => JSON.pretty_generate(Data.canonical(result.policy_report)) + "\n",
        "README.md" => result.readme
      }
      files.each { |name, content| atomic_write(File.join(directory, name), content) }
      result.runtime_files.each do |name, content|
        atomic_write(File.join(directory, "runtime", name), content)
      end
      copy_production_assets(directory, result.components) if result.selection.dig("deployment", "environment") == "production"
    end
    private :write_package

    def validate_deployment_package(path)
      directory = File.directory?(path) ? File.expand_path(path) : nil
      package_result = directory ? validate_package(directory) : {"status" => "not-applicable"}
      compose_path = directory ? File.join(directory, "compose.yml") : path
      raise ValidationError, "Compose file not found: #{compose_path}" unless File.file?(compose_path)

      compose = Data.load_yaml(compose_path)
      validate_compose_structure(compose)
      required_variables = File.read(compose_path).scan(/\$\{([A-Z][A-Z0-9_]*):\?/).flatten.uniq.sort
      docker_result = validate_with_docker(compose_path, required_variables)
      {
        "status" => "passed",
        "compose" => compose_path,
        "services" => compose.fetch("services").keys.sort,
        "requiredVariables" => required_variables,
        "dockerCompose" => docker_result,
        "package" => package_result
      }
    end

    alias validate_generated validate_deployment_package

    def plan(selection_or_path)
      result = assemble(selection_or_path)
      {
        "product" => result.selection.dig("product", "name"),
        "edition" => result.selection.dig("product", "edition"),
        "deployment" => result.selection.fetch("deployment"),
        "repositories" => RepositoryDeclarations.validate(result.selection["repositories"]),
        "components" => result.components.map do |component|
          {
            "capability" => component.fetch("capability"),
            "implementation" => component.fetch("implementation"),
            "services" => component.fetch("services")
          }
        end,
        "artifacts" => result.lock.fetch("artifacts"),
        "policyStatus" => result.policy_report.fetch("status")
      }
    end

    def collect_secrets(selection_or_path, output_path)
      components = assemble(selection_or_path).components

      env_files = components.each_with_object([]) do |component, list|
        Array(component["secretsEnvFiles"]).each do |relative_path|
          list << relative_path if File.file?(File.join(repository.root, relative_path))
        end
      end.uniq
      raise ValidationError, "no .env files found for the selected components" if env_files.empty?

      key_sources = Hash.new { |hash, key| hash[key] = [] }
      env_files.each do |relative_path|
        File.foreach(File.join(repository.root, relative_path)) do |line|
          text = line.sub(/\A[[:space:]]*/, "").sub(/\Aexport[[:space:]]+/, "")
          next unless text =~ /\A([A-Za-z_][A-Za-z0-9_]*)[[:space:]]*=/

          key_sources[Regexp.last_match(1)] << relative_path
        end
      end

      duplicates = key_sources.select { |_key, sources| sources.length > 1 }
      unless duplicates.empty?
        details = duplicates.map { |key, sources| "#{key}: #{sources.uniq.join(', ')}" }.join("; ")
        raise ValidationError, "duplicate secret keys across .env files: #{details}"
      end

      lines = [
        "# Generated by Nexus Assembler #{VERSION}.",
        "# Regenerate this file after changing a service-level .env file."
      ]
      env_files.each do |relative_path|
        lines << ""
        lines << "# Source: #{relative_path}"
        lines << File.read(File.join(repository.root, relative_path)).chomp
      end
      destination = File.expand_path(output_path)
      atomic_write(destination, lines.join("\n") + "\n", mode: 0o600)

      required_names = components.flat_map { |component| component.fetch("secrets", {}).keys }.uniq.sort
      {
        "output" => destination,
        "envFiles" => env_files,
        "missingRequired" => (required_names - key_sources.keys).sort
      }
    end

    private

    def validate_selection(selection)
      raise ValidationError, "blueprint must be a mapping" unless selection.is_a?(Hash)
      reject_unknown_keys!(selection, %w[apiVersion product deployment registry capabilities repositories], "blueprint")
      unless selection["apiVersion"] == "nexus.io/composition/v1alpha1"
        raise ValidationError, "apiVersion must be nexus.io/composition/v1alpha1"
      end

      product = selection["product"]
      deployment = selection["deployment"]
      raise ValidationError, "product must be a mapping" unless product.is_a?(Hash)
      raise ValidationError, "deployment must be a mapping" unless deployment.is_a?(Hash)
      if selection.key?("registry") && !selection["registry"].is_a?(Hash)
        raise ValidationError, "registry must be a mapping"
      end
      if selection.key?("capabilities") && !selection["capabilities"].is_a?(Hash)
        raise ValidationError, "capabilities must be a mapping"
      end
      RepositoryDeclarations.validate(selection["repositories"])
      reject_unknown_keys!(product, %w[name edition description], "product")
      reject_unknown_keys!(deployment, %w[target environment assurance], "deployment")
      reject_unknown_keys!(selection["registry"], %w[host namespace policy], "registry") if selection["registry"].is_a?(Hash)

      name = product["name"].to_s
      unless name.match?(/\A[a-z][a-z0-9-]{1,62}\z/)
        raise ValidationError, "product.name must be a lowercase DNS-style name"
      end

      edition = repository.load_dimension("editions", product.fetch("edition"))
      environment = repository.load_dimension("environments", deployment.fetch("environment"))
      target = repository.load_dimension("targets", deployment.fetch("target"))
      assurance = repository.load_dimension("assurance", deployment.fetch("assurance"))

      unless Array(target["allowedEnvironments"]).include?(deployment.fetch("environment"))
        raise ValidationError, "#{deployment['target']} does not support #{deployment['environment']}"
      end
      if deployment["assurance"] == "high-assurance" &&
         !(deployment["target"] == "self-hosted" && deployment["environment"] == "production")
        raise ValidationError, "high-assurance requires self-hosted production"
      end

      registry_required = assurance.fetch("privateRegistry", "optional").start_with?("required") ||
                          Array(target["registryRequiredIn"]).include?(deployment["environment"])
      registry = selection["registry"] || {}
      if registry_required && registry["host"].to_s.strip.empty?
        raise ValidationError, "registry.host is required for this target or assurance profile"
      end
      if registry_required && registry["namespace"].to_s.strip.empty?
        raise ValidationError, "registry.namespace is required for this target or assurance profile"
      end
      if assurance["privateRegistry"] == "required-exclusive" && registry["policy"] != "private-only"
        raise ValidationError, "high-assurance requires registry.policy private-only"
      end

      {
        edition: edition,
        environment: environment,
        target: target,
        assurance: assurance,
        registry_required: registry_required
      }
    rescue KeyError => e
      raise ValidationError, "missing required blueprint field #{e.key.inspect}"
    end

    def reject_unknown_keys!(mapping, allowed, label)
      unknown = mapping.keys.map(&:to_s) - allowed
      raise ValidationError, "unknown #{label} fields: #{unknown.sort.join(', ')}" unless unknown.empty?
    end

    def resolve_components(selection, edition)
      choices = Data.canonical(edition.fetch("defaults", {}))
      overrides = selection.fetch("capabilities", {}) || {}
      raise ValidationError, "capabilities must be a mapping" unless overrides.is_a?(Hash)

      overrides.each do |capability, value|
        implementation, enabled = normalize_capability_choice(value)
        if enabled
          choices[capability] = implementation
        else
          choices.delete(capability)
        end
      end

      required = Array(edition["required"])
      missing_required = required.reject { |capability| choices.key?(capability) }
      unless missing_required.empty?
        raise ValidationError, "edition requires capabilities: #{missing_required.join(', ')}"
      end

      disallowed = choices.keys - Array(edition["allowed"])
      unless disallowed.empty?
        raise ValidationError, "edition does not allow capabilities: #{disallowed.join(', ')}"
      end

      resolved = {}
      visiting = {}
      resolver = lambda do |capability, implementation|
        return if resolved.key?(capability)
        raise ValidationError, "cyclic dependency involving #{capability}" if visiting[capability]

        implementations = repository.catalog[capability]
        unless implementations && implementations[implementation]
          available = implementations ? implementations.keys.sort.join(", ") : "none"
          raise ValidationError, "unknown implementation #{capability}/#{implementation}; available: #{available}"
        end

        visiting[capability] = true
        component = implementations.fetch(implementation)
        entitlement = component["entitlement"]
        if entitlement && !Array(edition["entitlements"]).include?(entitlement)
          raise ValidationError, "#{capability}/#{implementation} requires edition entitlement #{entitlement}"
        end
        Array(component["dependencies"]).each do |dependency|
          dependency_implementation = choices[dependency] || edition.fetch("defaults", {})[dependency]
          if dependency_implementation.nil?
            candidates = repository.catalog.fetch(dependency, {})
            dependency_implementation = candidates.keys.first if candidates.length == 1
          end
          raise ValidationError, "#{capability} requires unselected capability #{dependency}" unless dependency_implementation

          choices[dependency] ||= dependency_implementation
          resolver.call(dependency, dependency_implementation)
        end
        visiting.delete(capability)
        resolved[capability] = component
      end

      choices.keys.sort.each { |capability| resolver.call(capability, choices.fetch(capability)) }
      resolved.keys.sort.map { |capability| resolved.fetch(capability) }
    end

    def normalize_capability_choice(value)
      if value.is_a?(String)
        return [value, false] if value == "disabled"
        return [value, true]
      end
      unless value.is_a?(Hash) && value["implementation"].is_a?(String)
        raise ValidationError, "capability choice must be an implementation string or mapping"
      end
      [value.fetch("implementation"), value.fetch("enabled", true)]
    end

    def assemble_compose(selection, components)
      compose = Data.load_yaml(File.join(repository.composition_root, "base.compose.yml"))
      components.each do |component|
        fragment = Data.load_yaml(File.join(repository.root, component.fetch("fragment")))
        compose = Data.deep_merge(compose, fragment)
      end
      product_name = selection.dig("product", "name")
      compose["name"] = "#{product_name}-#{selection.dig("deployment", "environment")}"
      compose.fetch("networks").fetch("system")["name"] = "#{product_name}-system"
      validate_compose_structure(compose)
      compose
    end

    def apply_deployment_policy!(compose, selection, components, context)
      environment_id = selection.dig("deployment", "environment")
      assurance_id = selection.dig("deployment", "assurance")
      production = environment_id == "production"
      hardened = %w[hardened high-assurance].include?(assurance_id)
      artifacts = []

      artifact_index = components.each_with_object({}) do |component, index|
        component.fetch("artifacts").each do |service, artifact|
          index[service] = artifact.merge(
            "capability" => component.fetch("capability"),
            "implementation" => component.fetch("implementation")
          )
        end
      end

      compose.fetch("services").each do |service_name, service|
        service["restart"] = context.fetch(:environment).fetch("restartPolicy", "unless-stopped")
        artifact = artifact_index[service_name]
        if production || hardened
          raise ValidationError, "missing artifact policy for service #{service_name}" unless artifact
          service.delete("build")
          service["image"] = deployment_image(selection, artifact)
          service["pull_policy"] = "always"
        end

        if production
          if service.key?("env_file")
            service["env_file"] = ["${AUTH_ENV_FILE:?AUTH_ENV_FILE is required}"]
          end
          required_names = required_variable_names(components)
          service.replace(require_variables(service, required_names))
        end

        if hardened
          security_options = Array(service["security_opt"])
          security_options << "no-new-privileges:true"
          service["security_opt"] = security_options.uniq.sort
          service["privileged"] = false
        end

        artifacts << artifact_record(service_name, service, artifact)
      end

      if assurance_id == "high-assurance"
        compose.fetch("networks").fetch("system")["internal"] = true
      end

      if production
        prepare_production_mounts!(compose, components)
        prepare_production_gateway!(compose, components)
      end

      artifacts.sort_by { |artifact| artifact.fetch("service") }
    end

    def deployment_image(selection, artifact)
      registry = selection.fetch("registry")
      host = registry.fetch("host").sub(%r{/$}, "")
      namespace = registry.fetch("namespace").gsub(%r{\A/+|/+$}, "")
      repository_name = artifact.fetch("repository")
      digest_variable = artifact.fetch("digestVariable")
      "#{host}/#{namespace}/#{repository_name}@${#{digest_variable}:?#{digest_variable} is required}"
    end

    def required_variable_names(components)
      names = []
      components.each do |component|
        names.concat(component.fetch("secrets", {}).keys)
        component.fetch("configuration", {}).each do |name, definition|
          names << name if definition["productionRequired"]
        end
      end
      names << "AUTH_ENV_FILE" if components.any? { |component| component.fetch("capability") == "authentication" }
      names.uniq.sort
    end

    def require_variables(value, names)
      Data.transform(value) do |item|
        next item unless item.is_a?(String)

        names.reduce(item) do |text, name|
          text.gsub(/\$\{#{Regexp.escape(name)}:-[^}]*\}/, "${#{name}:?#{name} is required}")
        end
      end
    end

    def artifact_record(service_name, service, artifact)
      {
        "service" => service_name,
        "capability" => artifact.fetch("capability"),
        "implementation" => artifact.fetch("implementation"),
        "mode" => artifact.fetch("mode"),
        "source" => artifact["source"],
        "upstream" => artifact["upstream"],
        "repository" => artifact.fetch("repository"),
        "digestVariable" => artifact.fetch("digestVariable"),
        "deploymentImage" => service["image"],
        "digestResolved" => service["image"].to_s.match?(/@sha256:[a-f0-9]{64}\z/),
        "runtimeBuild" => service.key?("build")
      }.reject { |_key, value| value.nil? }
    end

    def render_environment_example(selection, components, artifacts, context)
      development = selection.dig("deployment", "environment") == "development"
      lines = [
        "# Generated by Nexus Assembler #{VERSION}; values are examples, never secrets.",
        "# Copy to a private environment file and replace every required value.",
        ""
      ]

      configuration = components.each_with_object({}) do |component, result|
        component.fetch("configuration", {}).each { |name, value| result[name] ||= value }
      end
      configuration["AUTH_ENV_FILE"] ||= {
        "description" => "Absolute path to Keycloak and PostgreSQL runtime environment values",
        "productionRequired" => true
      } if components.any? { |component| component.fetch("capability") == "authentication" }

      configuration.keys.sort.each do |name|
        definition = configuration.fetch(name)
        next if definition["scope"] == "authentication-env"

        lines << "# #{definition['description']}" if definition["description"]
        value = development ? definition.fetch("developmentDefault", "") : ""
        lines << "#{name}=#{value}"
        lines << ""
      end

      secrets = components.each_with_object({}) do |component, result|
        component.fetch("secrets", {}).each { |name, value| result[name] ||= value }
      end
      unless secrets.empty?
        lines << "# Secrets: supply through the selected external secret workflow."
        secrets.keys.sort.each do |name|
          next if secrets[name]["scope"] == "authentication-env"

          lines << "# #{secrets[name]['description']}" if secrets[name]["description"]
          lines << "#{name}="
        end
        lines << ""
      end

      if context.fetch(:registry_required)
        lines << "# Immutable artifact digests produced by the approved build or mirror pipeline."
        artifacts.map { |artifact| artifact.fetch("digestVariable") }.uniq.sort.each do |name|
          lines << "#{name}="
        end
        lines << ""
      end
      lines.join("\n")
    end

    def render_runtime_files(selection, components)
      authentication = components.find { |component| component.fetch("capability") == "authentication" }
      return {} unless authentication

      production = selection.dig("deployment", "environment") == "production"
      hostname = production ? "" : "auth.localhost"
      lines = [
        "# Generated authentication runtime environment contract.",
        "# Copy to a private file, replace blank secrets, and set AUTH_ENV_FILE",
        "# in the root Compose interpolation environment to its absolute path.",
        "KC_DB=postgres",
        "KC_DB_URL_HOST=keycloak-db",
        "KC_DB_URL_PORT=5432",
        "KC_DB_URL_DATABASE=keycloak",
        "KC_DB_USERNAME=keycloak",
        "KC_DB_PASSWORD=",
        "KC_DB_POOL_MIN_SIZE=10",
        "KC_DB_POOL_MAX_SIZE=50",
        "KC_HOSTNAME=#{hostname}",
        "KC_HOSTNAME_STRICT=#{production ? 'true' : 'false'}",
        "KC_PROXY_HEADERS=xforwarded",
        "KC_HTTP_ENABLED=true",
        "KC_BOOTSTRAP_ADMIN_USERNAME=",
        "KC_BOOTSTRAP_ADMIN_PASSWORD=",
        "POSTGRES_DB=keycloak",
        "POSTGRES_USER=keycloak",
        "POSTGRES_PASSWORD=",
        ""
      ]
      {"auth.env.example" => lines.join("\n")}
    end

    def render_secrets_required(components)
      secrets = components.each_with_object({}) do |component, result|
        component.fetch("secrets", {}).each do |name, definition|
          result[name] ||= definition.merge("capabilities" => [])
          result[name]["capabilities"] << component.fetch("capability")
        end
      end
      lines = ["# Required runtime secrets; this file contains names only."]
      secrets.keys.sort.each do |name|
        definition = secrets.fetch(name)
        lines << "#{name}\t#{definition['capabilities'].uniq.sort.join(',')}\t#{definition['description']}"
      end
      lines.join("\n") + "\n"
    end

    def build_plan(selection, components, artifacts, context)
      assurance = context.fetch(:assurance)
      {
        "apiVersion" => "nexus.io/build-plan/v1alpha1",
        "product" => selection.dig("product", "name"),
        "environment" => selection.dig("deployment", "environment"),
        "assurance" => selection.dig("deployment", "assurance"),
        "registry" => selection["registry"],
        "requirements" => {
          "sbom" => !!assurance["requireSbom"],
          "provenance" => !!assurance["requireProvenance"],
          "signature" => !!assurance["requireSignature"],
          "reproducibleBuild" => !!assurance["requireReproducibleBuild"]
        },
        "artifacts" => artifacts.map do |artifact|
          actions = artifact["mode"] == "internal-build" ? ["build"] : ["resolve-upstream-digest", "verify-upstream", "mirror"]
          actions += ["scan", "generate-sbom", "attest-provenance", "sign", "push"]
          artifact.merge("actions" => actions)
        end
      }
    end

    def lock_file(selection, components, artifacts)
      blueprint_json = JSON.generate(Data.canonical(selection))
      {
        "apiVersion" => "nexus.io/composition-lock/v1alpha1",
        "assembler" => {"name" => "nexus-assembler", "version" => VERSION},
        "blueprintDigest" => "sha256:#{Digest::SHA256.hexdigest(blueprint_json)}",
        "components" => components.map do |component|
          {
            "capability" => component.fetch("capability"),
            "implementation" => component.fetch("implementation"),
            "fragment" => component.fetch("fragment")
          }
        end,
        "artifacts" => artifacts
      }
    end

    def evaluate_policies(selection, components, compose, artifacts, context)
      production = selection.dig("deployment", "environment") == "production"
      hardened = %w[hardened high-assurance].include?(selection.dig("deployment", "assurance"))
      registry_host = selection.dig("registry", "host")
      services = compose.fetch("services")
      private_services = components.flat_map { |component| Array(component.dig("security", "privateServices")) }.uniq

      checks = []
      add_check(checks, "unique-services", true, true, "service names are unique after dependency resolution")
      add_check(checks, "runtime-builds-forbidden", !production || services.values.none? { |service| service.key?("build") }, production,
                "production Compose contains no build instructions")
      add_check(checks, "immutable-images", !hardened || artifacts.all? { |artifact| artifact["deploymentImage"].to_s.include?("@${") }, hardened,
                "hardened artifacts are selected by required digest variables")
      add_check(checks, "private-registry-only", !hardened || artifacts.all? { |artifact| artifact["deploymentImage"].to_s.start_with?("#{registry_host}/") }, hardened,
                "hardened runtime images resolve through the selected private registry")
      add_check(checks, "no-development-secret-defaults", !production || !Data.yaml(compose).include?("change-me"), production,
                "production output contains no change-me secret defaults")
      add_check(checks, "privileged-forbidden", !hardened || services.values.none? { |service| service["privileged"] == true }, hardened,
                "hardened services are not privileged")
      add_check(checks, "private-ports-forbidden", private_services.none? { |name| services.fetch(name, {}).key?("ports") }, true,
                "private dependencies publish no host ports")
      add_check(checks, "no-new-privileges", !hardened || services.values.all? { |service| Array(service["security_opt"]).include?("no-new-privileges:true") }, hardened,
                "hardened services deny privilege escalation")
      gateway = services["gateway"] || {}
      tls_configured = gateway.dig("environment", "GATEWAY_TLS_REDIRECT") == "1" &&
                       Array(gateway["ports"]).include?("${GATEWAY_HTTPS_PORT:-443}:443") &&
                       Array(gateway["volumes"]).any? { |mount| mount.to_s.include?("/etc/nginx/ssl:ro") }
      add_check(checks, "production-tls", !production || tls_configured, production,
                "production gateway redirects to HTTPS and requires mounted certificate material")

      selected_capabilities = components.map { |component| component.fetch("capability") }
      dormant_routes = %w[website authentication service-status observability].reject { |capability| selected_capabilities.include?(capability) }
      warnings = dormant_routes.map do |capability|
        {
          "id" => "dormant-gateway-route-#{capability}",
          "message" => "the current gateway image contains a route template for unselected capability #{capability}; requests fail closed with no upstream"
        }
      end
      if selection.dig("deployment", "assurance") == "high-assurance"
        warnings << {
          "id" => "host-controls-outside-compose",
          "message" => "host hardening, signature admission, external secret injection, encrypted backup, and external audit require deployment-platform enforcement"
        }
      end

      failures = checks.select { |check| check["required"] && check["status"] != "passed" }
      {
        "apiVersion" => "nexus.io/policy-report/v1alpha1",
        "status" => failures.empty? ? "passed" : "failed",
        "product" => selection.dig("product", "name"),
        "deployment" => selection.fetch("deployment"),
        "checks" => checks,
        "warnings" => warnings,
        "failures" => failures.map { |failure| failure.fetch("id") }
      }
    end

    def add_check(checks, id, passed, required, message)
      checks << {
        "id" => id,
        "status" => passed ? "passed" : "failed",
        "required" => !!required,
        "message" => message
      }
    end

    def render_readme(selection, components, policy_report)
      product = selection.dig("product", "name")
      deployment = selection.fetch("deployment")
      capability_lines = components.map do |component|
        "- `#{component['capability']}` using `#{component['implementation']}`"
      end.join("\n")
      required_hint = deployment["environment"] == "production" ?
        "Populate `.env.example`, copy `runtime/auth.env.example` to a private runtime file, set `AUTH_ENV_FILE` to its absolute path, and resolve every image digest before deployment." :
        "Copy `.env.example` to `.env` when local overrides are needed."
      compose_command = deployment["environment"] == "production" ?
        "docker compose --env-file .env -f compose.yml up -d" :
        "docker compose -f compose.yml up -d --build"

      <<~MARKDOWN
        # #{product} Deployment Package

        This deployment package was produced by Nexus Assembler #{VERSION}. Do not
        edit assembled files directly; change the blueprint or catalog and reassemble.

        ## Blueprint

        - Edition: `#{selection.dig('product', 'edition')}`
        - Target: `#{deployment['target']}`
        - Environment: `#{deployment['environment']}`
        - Assurance: `#{deployment['assurance']}`
        - Policy status: `#{policy_report['status']}`

        ## Capabilities

        #{capability_lines}

        ## Use

        #{required_hint}

        ```sh
        nexus validate .
        #{compose_command}
        ```

        Review `policy-report.json`, `compose.lock.yaml`, `build-plan.yaml`, and
        `secrets.required` before deployment. A passed Compose policy report does
        not replace host, registry, secret-provider, backup, or operational controls.
      MARKDOWN
    end

    def prepare_production_mounts!(compose, components)
      components.each do |component|
        Array(component.dig("production", "volumeRewrites")).each do |rewrite|
          service = compose.dig("services", rewrite.fetch("service"))
          next unless service

          prefix = rewrite.fetch("matchPrefix")
          if rewrite["namedVolume"]
            named_volume = rewrite.fetch("namedVolume")
            service["volumes"] = Array(service["volumes"]).map do |mount|
              text = mount.to_s
              text.start_with?(prefix) ? "#{named_volume}:#{text[prefix.length..]}" : text
            end
            compose["volumes"] ||= {}
            compose["volumes"][named_volume] ||= {}
          else
            replacement = rewrite.fetch("replacement")
            service["volumes"] = Array(service["volumes"]).map do |mount|
              text = mount.to_s
              text.start_with?(prefix) ? "#{replacement}#{text[prefix.length..]}" : text
            end
          end
        end
      end
    end

    def prepare_production_gateway!(compose, components)
      gateway = compose.dig("services", "gateway")
      return unless gateway

      components.each do |component|
        production = component["production"] || {}

        Array(production["environmentOverrides"]).each do |override|
          service = compose.dig("services", override.fetch("service"))
          next unless service

          service["environment"] ||= {}
          service["environment"][override.fetch("key")] = override.fetch("value")
        end

        Array(production["portMappings"]).each do |mapping|
          service = compose.dig("services", mapping.fetch("service"))
          next unless service

          service["ports"] = Array(service["ports"])
          service["ports"] << mapping.fetch("mapping")
          service["ports"] = service["ports"].uniq
        end

        Array(production["gatewayVolumes"]).each do |volume|
          gateway["volumes"] = Array(gateway["volumes"])
          gateway["volumes"] << volume
        end
      end
    end

    def compose_for_output(compose, selection, destination)
      output = Marshal.load(Marshal.dump(compose))
      return output unless selection.dig("deployment", "environment") == "development"

      output.fetch("services").each_value do |service|
        if service["build"].is_a?(Hash) && service["build"]["context"].is_a?(String)
          service["build"]["context"] = rebase_repository_path(service["build"]["context"], destination)
        end
        service["env_file"] = Array(service["env_file"]).map do |entry|
          if entry.is_a?(Hash) && entry["path"].is_a?(String)
            entry.merge("path" => rebase_repository_path(entry["path"], destination))
          elsif entry.is_a?(String)
            rebase_repository_path(entry, destination)
          else
            entry
          end
        end if service.key?("env_file")
        service["volumes"] = Array(service["volumes"]).map do |mount|
          rebase_bind_mount(mount, destination)
        end if service.key?("volumes")
      end
      output
    end

    def rebase_repository_path(path, destination)
      return path unless path.start_with?("./")

      absolute = File.expand_path(path, repository.root)
      Pathname.new(absolute).relative_path_from(Pathname.new(destination)).to_s
    end

    def rebase_bind_mount(mount, destination)
      return mount unless mount.is_a?(String) && mount.start_with?("./")

      source, remainder = mount.split(":", 2)
      rebased = rebase_repository_path(source, destination)
      remainder ? "#{rebased}:#{remainder}" : rebased
    end

    def copy_production_assets(destination, components)
      components.each do |component|
        Array(component.dig("production", "assetCopies")).each do |copy|
          source = File.join(repository.root, copy.fetch("source"))
          next unless File.directory?(source)

          target = File.join(destination, copy.fetch("destination"))
          FileUtils.mkdir_p(target)
          Dir[File.join(source, "*")].sort.each do |path|
            FileUtils.cp_r(path, target)
          end
        end
      end
    end

    def validate_compose_structure(compose)
      raise ValidationError, "Compose document must be a mapping" unless compose.is_a?(Hash)
      services = compose["services"]
      raise ValidationError, "Compose services must be a non-empty mapping" unless services.is_a?(Hash) && !services.empty?
      services.each do |name, service|
        raise ValidationError, "service #{name} must be a mapping" unless service.is_a?(Hash)
        unless service.key?("image") || service.key?("build")
          raise ValidationError, "service #{name} must declare image or build"
        end
        health_test = service.dig("healthcheck", "test")
        if health_test && (!health_test.is_a?(Array) || health_test.any? { |item| !item.is_a?(String) })
          raise ValidationError, "service #{name} healthcheck.test must be a list of strings"
        end
      end
      true
    end

    def validate_package(directory)
      required = %w[
        .env.example
        README.md
        build-plan.yaml
        compose.lock.yaml
        compose.yml
        policy-report.json
        secrets.required
      ]
      required << "runtime/auth.env.example" if File.read(File.join(directory, "compose.yml")).include?("AUTH_ENV_FILE")
      missing = required.reject { |name| File.file?(File.join(directory, name)) }
      raise ValidationError, "deployment package is missing: #{missing.join(', ')}" unless missing.empty?

      blueprint_path = ["blueprint.yaml", "selection.yaml"]
        .map { |name| File.join(directory, name) }
        .find { |candidate| File.file?(candidate) }
      raise ValidationError, "deployment package is missing: blueprint.yaml" unless blueprint_path

      blueprint = Data.load_yaml(blueprint_path)
      lock = Data.load_yaml(File.join(directory, "compose.lock.yaml"))
      policy = JSON.parse(File.read(File.join(directory, "policy-report.json")))
      compose = Data.load_yaml(File.join(directory, "compose.yml"))
      expected_digest = "sha256:#{Digest::SHA256.hexdigest(JSON.generate(Data.canonical(blueprint)))}"
      locked_digest = lock["blueprintDigest"] || lock["selectionDigest"]
      unless locked_digest == expected_digest
        raise ValidationError, "blueprint digest does not match compose.lock.yaml"
      end
      unless policy["status"] == "passed"
        raise PolicyError, "deployment package policy status is #{policy['status'].inspect}"
      end

      Array(lock["artifacts"]).each do |artifact|
        service = compose.dig("services", artifact.fetch("service"))
        raise ValidationError, "locked service is absent: #{artifact['service']}" unless service
        unless service["image"] == artifact["deploymentImage"]
          raise ValidationError, "image for #{artifact['service']} differs from compose.lock.yaml"
        end
      end

      {"status" => "passed", "blueprintDigest" => expected_digest}
    rescue JSON::ParserError => e
      raise ValidationError, "invalid policy-report.json: #{e.message}"
    end

    def validate_with_docker(compose_path, required_variables)
      docker = system("docker", "compose", "version", out: File::NULL, err: File::NULL)
      return {"status" => "skipped", "reason" => "docker compose is unavailable"} unless docker

      runtime_environment = Tempfile.new(["nexus-compose-runtime", ".env"])
      interpolation_environment = Tempfile.new(["nexus-compose-validation", ".env"])
      begin
        runtime_environment.write("NEXUS_VALIDATION=1\n")
        runtime_environment.flush
        required_variables.each do |name|
          value = if name == "AUTH_ENV_FILE"
                    runtime_environment.path
                  elsif name.end_with?("_IMAGE_DIGEST")
                    "sha256:#{'a' * 64}"
                  elsif name.end_with?("_DIR")
                    "/tmp/nexus-compose-validation"
                  elsif name.end_with?("_PORT")
                    "8080"
                  else
                    "nexus-validation"
                  end
          interpolation_environment.write("#{name}=#{value}\n")
        end
        interpolation_environment.flush
        _stdout, stderr, status = Open3.capture3(
          "docker", "compose",
          "--env-file", interpolation_environment.path,
          "-f", compose_path,
          "config", "--quiet"
        )
        raise ValidationError, "docker compose config failed: #{stderr.strip}" unless status.success?

        {
          "status" => "passed",
          "syntheticRequiredValues" => !required_variables.empty?
        }
      ensure
        interpolation_environment.close!
        runtime_environment.close!
      end
    end

    def atomic_write(path, content, mode: nil)
      directory = File.dirname(path)
      FileUtils.mkdir_p(directory)
      temporary = Tempfile.new([File.basename(path), ".tmp"], directory)
      begin
        temporary.chmod(mode) if mode
        temporary.write(content)
        temporary.flush
        temporary.fsync
        temporary.close
        File.rename(temporary.path, path)
      ensure
        temporary.close! if temporary
      end
    end
  end

  # Backward-compatible API name for integrations that still instantiate Compiler.
  Compiler = Assembler
end
