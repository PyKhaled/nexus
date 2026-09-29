#!/usr/bin/env python3
"""
secreport — normalize, enrich, triage, report and gate DevSecOps scanner output.

    python tools/secreport.py run  --input raw-artifacts --out reports \
        --policy security/risk-policy.yaml --exceptions security/exceptions.yaml \
        --baseline .baseline/baseline.json --pdf --xlsx --sarif --markdown

    python tools/secreport.py gate --results reports/findings.json \
        --policy security/risk-policy.yaml

Design notes
------------
* Scanners never decide pass/fail. They emit evidence. This module is the only
  component that makes a decision, so the decision is consistent and auditable.
* Every finding gets a stable fingerprint, so "new vs. pre-existing" is real
  and a developer is never blamed for debt they did not create.
* Enrichment uses only free, open data: CISA KEV and FIRST EPSS. Both are
  fetched over plain HTTPS with a hard timeout and a graceful offline fallback,
  because a security tool that fails closed on a network blip is a liability.
* 100% open source dependencies. No vendor account, token or subscription.

Licence: MIT.
"""
from __future__ import annotations

import argparse
import csv
import fnmatch
import gzip
import hashlib
import io
import json
import os
import re
import sys
import urllib.request
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.exit("pyyaml is required: pip install -r tools/requirements.txt")

KEV_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
EPSS_URL = "https://epss.empiricalsecurity.com/epss_scores-current.csv.gz"
NET_TIMEOUT = 25

SEVERITY_ORDER = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]
CATEGORIES = [
    "SECRETS", "SAST", "SCA", "IAC", "CONTAINER", "DAST", "CI_SUPPLY_CHAIN", "LICENSE",
]


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------
@dataclass
class Finding:
    tool: str
    category: str
    rule_id: str
    title: str
    severity: str = "MEDIUM"
    description: str = ""
    file: str = ""
    line: int = 0
    package: str = ""
    installed_version: str = ""
    fixed_version: str = ""
    cve: str = ""
    cwe: str = ""
    references: list[str] = field(default_factory=list)
    remediation: str = ""
    verified: bool = False          # secret confirmed live
    fix_available: bool = False
    dev_dependency: bool = False
    published: str = ""             # ISO date of CVE publication, if known

    # populated by enrichment / scoring
    epss: float = 0.0
    kev: bool = False
    confirmed_by: list[str] = field(default_factory=list)
    risk_score: float = 0.0
    risk_factors: list[str] = field(default_factory=list)
    status: str = "new"             # new | existing
    accepted: bool = False
    acceptance: dict[str, Any] = field(default_factory=dict)
    sla_due: str = ""
    triage_note: str = ""
    fingerprint: str = ""

    def compute_fingerprint(self) -> str:
        """Stable across line-number churn: identity is rule + location + subject."""
        # NOTE: the tool name is deliberately NOT part of the identity. Two
        # engines reporting the same CVE in the same package are one finding,
        # and collapsing them is what makes multi-tool confirmation possible.
        parts = [
            self.rule_id.lower(),
            (self.cve or "").upper(),
            (self.package or "").lower(),
            normalise_path(self.file),
        ]
        self.fingerprint = hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]
        return self.fingerprint


def normalise_path(p: str) -> str:
    p = (p or "").replace("\\", "/").lstrip("./")
    for prefix in ("/github/workspace/", "/repo/", "/src/"):
        if p.startswith(prefix):
            p = p[len(prefix):]
    return p


def norm_sev(value: Any) -> str:
    s = str(value or "").strip().upper()
    mapping = {
        "ERROR": "HIGH", "WARNING": "MEDIUM", "NOTE": "LOW", "NONE": "INFO",
        "INFORMATIONAL": "INFO", "INFORMATION": "INFO", "UNKNOWN": "LOW",
        "NEGLIGIBLE": "LOW", "MODERATE": "MEDIUM", "IMPORTANT": "HIGH",
        "FATAL": "CRITICAL", "BLOCKER": "CRITICAL", "MAJOR": "HIGH", "MINOR": "LOW",
        "WARN": "MEDIUM", "FAIL": "HIGH", "PASS": "INFO", "SKIP": "INFO",
    }
    if s in SEVERITY_ORDER:
        return s
    return mapping.get(s, "MEDIUM")


CVE_RE = re.compile(r"(CVE-\d{4}-\d{4,7}|GHSA-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4})", re.I)
CWE_RE = re.compile(r"(CWE-\d+)", re.I)


def first_match(pattern: re.Pattern, *texts: str) -> str:
    for t in texts:
        if not t:
            continue
        m = pattern.search(t)
        if m:
            return m.group(1).upper()
    return ""


# ---------------------------------------------------------------------------
# Parsers — one per output shape, all returning list[Finding]
# ---------------------------------------------------------------------------
TOOL_CATEGORY = {
    "semgrep": "SAST", "codeql": "SAST", "opengrep": "SAST", "bandit": "SAST",
    "gitleaks": "SECRETS", "trufflehog": "SECRETS",
    "trivy": "SCA", "grype": "SCA", "osv-scanner": "SCA", "osv": "SCA", "syft": "SCA",
    "checkov": "IAC", "kics": "IAC", "conftest": "IAC", "terrascan": "IAC",
    "kube-linter": "IAC", "tfsec": "IAC",
    "hadolint": "CONTAINER", "dockle": "CONTAINER",
    "zap": "DAST", "owasp zap": "DAST", "nuclei": "DAST",
    "zizmor": "CI_SUPPLY_CHAIN", "actionlint": "CI_SUPPLY_CHAIN",
    "scorecard": "CI_SUPPLY_CHAIN", "ossf scorecard": "CI_SUPPLY_CHAIN",
}


def guess_category(tool: str, filename: str = "") -> str:
    t = tool.lower()
    for key, cat in TOOL_CATEGORY.items():
        if key in t:
            if key == "trivy":
                low = filename.lower()
                if "config" in low:
                    return "IAC"
                if "image" in low:
                    return "CONTAINER"
            return cat
    return "SAST"


def trivy_field(label: str, text: str) -> str:
    """Read one `Label: value` line out of a Trivy SARIF message.

    Anchored to a single line on purpose. The obvious version of this --
    one regex with `Label:\\s*(\\S+)` per field, joined by `.*?` under re.S --
    silently crosses newlines, because `\\s` matches one. Trivy writes an
    unfixed vulnerability as

        Fixed Version:
        Link: [CVE-2026-13221](https://avd.aquasec.com/nvd/cve-2026-13221)

    so `\\s*` ate the newline and `(\\S+)` bound to `Link:` on the line below.
    Every unfixed CVE came back claiming a fixed version of "Link:", which then
    set fix_available and scored it with the fix_available multiplier (x1.1)
    instead of the unfixed one (x0.85) -- inverting the intended weighting for
    exactly the findings nothing can be done about today.
    """
    m = re.search(rf"^{re.escape(label)}:[^\S\r\n]*(.*)$", text, re.M)
    return m.group(1).strip() if m else ""


def parse_sarif(path: Path) -> list[Finding]:
    """Generic SARIF 2.1.0 reader. Covers Semgrep, Trivy, Checkov, Gitleaks,
    CodeQL, Hadolint, zizmor, Scorecard and anything else that speaks SARIF."""
    out: list[Finding] = []
    try:
        doc = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return out

    for run in doc.get("runs", []):
        driver = (run.get("tool") or {}).get("driver") or {}
        tool = driver.get("name") or path.stem
        rules = {r.get("id"): r for r in driver.get("rules", []) if isinstance(r, dict)}
        category = guess_category(tool, path.name)

        for res in run.get("results", []):
            rule_id = res.get("ruleId") or res.get("rule", {}).get("id") or "unknown"
            rule = rules.get(rule_id, {})
            msg = (res.get("message") or {}).get("text", "") or ""
            help_txt = ((rule.get("help") or {}).get("text")
                        or (rule.get("fullDescription") or {}).get("text") or "")
            short = ((rule.get("shortDescription") or {}).get("text") or "")

            sev = res.get("level") or (rule.get("defaultConfiguration") or {}).get("level")
            props = {**(rule.get("properties") or {}), **(res.get("properties") or {})}
            for key in ("security-severity", "severity", "problem.severity", "tags"):
                if key in props and key != "tags":
                    raw = props[key]
                    try:  # security-severity is a CVSS-style number
                        num = float(raw)
                        sev = ("CRITICAL" if num >= 9 else "HIGH" if num >= 7
                               else "MEDIUM" if num >= 4 else "LOW")
                    except (TypeError, ValueError):
                        sev = raw
                    break

            file_path, line = "", 0
            locs = res.get("locations") or []
            if locs:
                phys = (locs[0].get("physicalLocation") or {})
                file_path = (phys.get("artifactLocation") or {}).get("uri", "")
                line = int((phys.get("region") or {}).get("startLine", 0) or 0)

            tags = props.get("tags") or []
            refs = [u for u in [rule.get("helpUri")] if u]

            f = Finding(
                tool=tool,
                category=category,
                rule_id=str(rule_id),
                title=(short or msg or str(rule_id))[:220],
                severity=norm_sev(sev),
                description=(msg or help_txt)[:2000],
                file=normalise_path(file_path),
                line=line,
                cve=first_match(CVE_RE, str(rule_id), msg, short, " ".join(map(str, tags))),
                cwe=first_match(CWE_RE, str(rule_id), " ".join(map(str, tags)), help_txt, short),
                references=refs,
                remediation=help_txt[:1200],
            )
            # Trivy encodes package data in the message; recover it.
            if pkg := trivy_field("Package", msg):
                f.package = pkg
                f.installed_version = trivy_field("Installed Version", msg)
                f.fixed_version = trivy_field("Fixed Version", msg)
                f.fix_available = bool(f.fixed_version)
            out.append(f)
    return out


def parse_trufflehog(path: Path) -> list[Finding]:
    out = []
    for line in path.read_text(errors="replace").splitlines():
        line = line.strip()
        if not line or not line.startswith("{"):
            continue
        try:
            d = json.loads(line)
        except Exception:
            continue
        meta = ((d.get("SourceMetadata") or {}).get("Data") or {})
        git = meta.get("Git") or meta.get("Filesystem") or {}
        verified = bool(d.get("Verified"))
        detector = d.get("DetectorName", "unknown")
        f = Finding(
            tool="trufflehog",
            category="SECRETS",
            rule_id=f"trufflehog.{detector}",
            title=f"{'VERIFIED live credential' if verified else 'Potential credential'}: {detector}",
            severity="CRITICAL" if verified else "MEDIUM",
            description=(
                f"Detector={detector}; verified against the provider API={verified}. "
                "A verified credential must be rotated immediately and the exposure "
                "window treated as a security incident."
            ),
            file=normalise_path(git.get("file", "")),
            line=int(git.get("line", 0) or 0),
            verified=verified,
            remediation="Revoke and rotate the credential, then purge it from git history "
                        "(git-filter-repo / BFG) and move it to a secrets manager.",
        )
        out.append(f)
    return out


def parse_grype(path: Path) -> list[Finding]:
    out = []
    try:
        doc = json.loads(path.read_text(errors="replace"))
    except Exception:
        return out
    for m in doc.get("matches", []):
        vuln = m.get("vulnerability") or {}
        art = m.get("artifact") or {}
        fix = (vuln.get("fix") or {})
        versions = fix.get("versions") or []
        loc = (art.get("locations") or [{}])[0].get("path", "")
        out.append(Finding(
            tool="grype",
            category="SCA",
            rule_id=vuln.get("id", "unknown"),
            title=f"{vuln.get('id','')} in {art.get('name','')} {art.get('version','')}",
            severity=norm_sev(vuln.get("severity")),
            description=(vuln.get("description") or "")[:2000],
            file=normalise_path(loc),
            package=art.get("name", ""),
            installed_version=art.get("version", ""),
            fixed_version=", ".join(versions),
            fix_available=bool(versions),
            cve=first_match(CVE_RE, vuln.get("id", "")),
            references=(vuln.get("urls") or [])[:5],
            remediation=(f"Upgrade {art.get('name','')} to {versions[0]}" if versions
                         else "No fixed version published yet — assess reachability and compensating controls."),
        ))
    return out


def parse_osv(path: Path) -> list[Finding]:
    out = []
    try:
        doc = json.loads(path.read_text(errors="replace"))
    except Exception:
        return out
    for res in doc.get("results", []):
        src = (res.get("source") or {}).get("path", "")
        for pkg in res.get("packages", []):
            info = pkg.get("package") or {}
            for v in pkg.get("vulnerabilities", []):
                sev = "MEDIUM"
                for s in v.get("severity", []) or []:
                    sev = norm_sev(s.get("type", "")) if s.get("type") in SEVERITY_ORDER else sev
                db = (v.get("database_specific") or {})
                if db.get("severity"):
                    sev = norm_sev(db["severity"])
                out.append(Finding(
                    tool="osv-scanner",
                    category="SCA",
                    rule_id=v.get("id", "unknown"),
                    title=f"{v.get('id','')}: {(v.get('summary') or '')[:150]}",
                    severity=sev,
                    description=(v.get("details") or v.get("summary") or "")[:2000],
                    file=normalise_path(src),
                    package=info.get("name", ""),
                    installed_version=info.get("version", ""),
                    cve=first_match(CVE_RE, v.get("id", ""), " ".join(v.get("aliases", []) or [])),
                    published=(v.get("published") or "")[:10],
                    references=[r.get("url", "") for r in (v.get("references") or [])][:5],
                ))
    return out


def parse_conftest(path: Path) -> list[Finding]:
    out = []
    try:
        doc = json.loads(path.read_text(errors="replace"))
    except Exception:
        return out
    if isinstance(doc, dict):
        doc = [doc]
    for res in doc:
        target = normalise_path(res.get("filename", ""))
        for kind, sev in (("failures", "HIGH"), ("warnings", "MEDIUM")):
            for item in res.get(kind) or []:
                msg = item.get("msg", "")
                out.append(Finding(
                    tool="conftest",
                    category="IAC",
                    rule_id=item.get("metadata", {}).get("id", "opa.policy"),
                    title=f"Policy violation: {msg[:180]}",
                    severity=sev,
                    description=msg,
                    file=target,
                    remediation="Amend the manifest to satisfy the organisational Rego policy "
                                "in .config/policy, or file a documented exception.",
                ))
    return out


def parse_dockle(path: Path) -> list[Finding]:
    out = []
    try:
        doc = json.loads(path.read_text(errors="replace"))
    except Exception:
        return out
    for d in doc.get("details", []):
        out.append(Finding(
            tool="dockle",
            category="CONTAINER",
            rule_id=d.get("code", "dockle"),
            title=d.get("title", "")[:220],
            severity=norm_sev(d.get("level")),
            description="; ".join(d.get("alerts", []) or [])[:2000],
            remediation="Follow the CIS Docker Benchmark guidance for this control.",
        ))
    return out


def parse_zap(path: Path) -> list[Finding]:
    out = []
    try:
        doc = json.loads(path.read_text(errors="replace"))
    except Exception:
        return out
    risk_map = {"0": "INFO", "1": "LOW", "2": "MEDIUM", "3": "HIGH"}
    for site in doc.get("site", []) or []:
        for a in site.get("alerts", []) or []:
            inst = (a.get("instances") or [{}])[0]
            out.append(Finding(
                tool="zap",
                category="DAST",
                rule_id=f"zap.{a.get('pluginid','')}",
                title=a.get("alert", "")[:220],
                severity=risk_map.get(str(a.get("riskcode", "1")), "LOW"),
                description=re.sub(r"<[^>]+>", "", a.get("desc", ""))[:2000],
                file=inst.get("uri", ""),
                cwe=f"CWE-{a['cweid']}" if a.get("cweid") not in (None, "", "-1") else "",
                remediation=re.sub(r"<[^>]+>", "", a.get("solution", ""))[:1200],
                references=[u for u in (a.get("reference", "") or "").split() if u.startswith("http")][:5],
            ))
    return out


def parse_nuclei(path: Path) -> list[Finding]:
    out = []
    for line in path.read_text(errors="replace").splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            d = json.loads(line)
        except Exception:
            continue
        info = d.get("info") or {}
        out.append(Finding(
            tool="nuclei",
            category="DAST",
            rule_id=d.get("template-id", "nuclei"),
            title=info.get("name", "")[:220],
            severity=norm_sev(info.get("severity")),
            description=(info.get("description") or "")[:2000],
            file=d.get("matched-at", ""),
            references=(info.get("reference") or [])[:5],
            remediation=info.get("remediation", "") or "",
        ))
    return out


def load_sbom(input_dir: Path) -> list[dict[str, str]]:
    comps: dict[tuple, dict[str, str]] = {}
    for p in input_dir.rglob("*.cdx.json"):
        try:
            doc = json.loads(p.read_text(errors="replace"))
        except Exception:
            continue
        for c in doc.get("components", []) or []:
            lic = ""
            for l in c.get("licenses", []) or []:
                lic = (l.get("license") or {}).get("id") or (l.get("license") or {}).get("name") or lic
            key = (c.get("name", ""), c.get("version", ""))
            comps[key] = {
                "name": c.get("name", ""),
                "version": c.get("version", ""),
                "type": c.get("type", ""),
                "license": lic,
                "purl": c.get("purl", ""),
                "source": p.name,
            }
    return sorted(comps.values(), key=lambda x: (x["name"].lower(), x["version"]))


PARSERS: list[tuple[str, Any]] = [
    ("*.sarif", parse_sarif),
    ("*sarif.json", parse_sarif),
    ("trufflehog*.json", parse_trufflehog),
    ("grype*.json", parse_grype),
    ("osv*.json", parse_osv),
    ("conftest*.json", parse_conftest),
    ("dockle*.json", parse_dockle),
    ("zap*.json", parse_zap),
    ("nuclei*.json*", parse_nuclei),
]


def collect(input_dir: Path) -> list[Finding]:
    findings: list[Finding] = []
    seen_files: set[Path] = set()
    for pattern, parser in PARSERS:
        for p in sorted(input_dir.rglob(pattern)):
            if p in seen_files or "sbom" in p.name.lower():
                continue
            seen_files.add(p)
            try:
                got = parser(p)
            except Exception as exc:  # a broken scanner output must not kill the report
                print(f"  ! could not parse {p.name}: {exc}", file=sys.stderr)
                continue
            print(f"  + {p.name:<34} {len(got):>5} findings ({parser.__name__})")
            findings.extend(got)
    return findings


# ---------------------------------------------------------------------------
# Enrichment: CISA KEV + FIRST EPSS (both free, open data)
# ---------------------------------------------------------------------------
def http_get(url: str) -> bytes | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "secreport/1.0"})
        with urllib.request.urlopen(req, timeout=NET_TIMEOUT) as r:
            return r.read()
    except Exception as exc:
        print(f"  ! threat-intel fetch failed for {url.split('/')[2]}: {exc}", file=sys.stderr)
        return None


def load_kev(cache: Path) -> set[str]:
    raw = http_get(KEV_URL)
    if raw:
        cache.write_bytes(raw)
    elif cache.exists():
        raw = cache.read_bytes()
        print("  · using cached KEV catalog", file=sys.stderr)
    if not raw:
        return set()
    try:
        doc = json.loads(raw)
        return {v["cveID"].upper() for v in doc.get("vulnerabilities", [])}
    except Exception:
        return set()


def load_epss(cache: Path) -> dict[str, float]:
    raw = http_get(EPSS_URL)
    if raw:
        cache.write_bytes(raw)
    elif cache.exists():
        raw = cache.read_bytes()
        print("  · using cached EPSS scores", file=sys.stderr)
    if not raw:
        return {}
    try:
        text = gzip.decompress(raw).decode("utf-8", errors="replace")
    except Exception:
        text = raw.decode("utf-8", errors="replace")
    scores: dict[str, float] = {}
    for row in csv.reader(io.StringIO(text)):
        if not row or row[0].startswith("#") or row[0].lower() == "cve":
            continue
        try:
            scores[row[0].upper()] = float(row[1])
        except (IndexError, ValueError):
            continue
    return scores


# ---------------------------------------------------------------------------
# Scoring, deduplication, exceptions, baseline
# ---------------------------------------------------------------------------
def dedupe(findings: list[Finding]) -> list[Finding]:
    by_fp: dict[str, Finding] = {}
    for f in findings:
        fp = f.compute_fingerprint()
        if fp in by_fp:
            keep = by_fp[fp]
            if keep.tool != f.tool and f.tool not in keep.confirmed_by:
                keep.confirmed_by.append(f.tool)
            # keep the worst severity and the richest remediation text
            if SEVERITY_ORDER.index(f.severity) < SEVERITY_ORDER.index(keep.severity):
                keep.severity = f.severity
            if len(f.remediation) > len(keep.remediation):
                keep.remediation = f.remediation
            if not keep.fixed_version and f.fixed_version:
                keep.fixed_version, keep.fix_available = f.fixed_version, True
        else:
            f.confirmed_by = [f.tool]
            by_fp[fp] = f
    return list(by_fp.values())


def in_non_prod(path: str, patterns: list[str]) -> bool:
    p = normalise_path(path)
    return any(p.startswith(pat) or fnmatch.fnmatch(p, f"*{pat}*") for pat in patterns)


def score(findings: list[Finding], policy: dict, kev: set[str], epss: dict[str, float]) -> None:
    sc = policy.get("scoring", {})
    base = sc.get("base", {})
    mul = sc.get("multipliers", {})
    ctx = policy.get("context", {})
    nonprod = ctx.get("non_production_paths", [])
    sla = policy.get("sla_days", {})
    today = date.today()

    for f in findings:
        cve = (f.cve or "").upper()
        f.kev = cve in kev
        f.epss = epss.get(cve, 0.0)

        s = float(base.get(f.severity, 30))
        factors: list[str] = [f"base:{f.severity}={s:.0f}"]

        def apply(name: str, key: str, cond: bool) -> None:
            nonlocal s
            if cond and key in mul:
                s *= float(mul[key])
                factors.append(f"{name}(x{mul[key]})")

        apply("CISA-KEV", "kev_listed", f.kev)
        apply("EPSS-high", "epss_high", f.epss >= sc.get("epss_high_threshold", 0.3))
        apply("EPSS-med", "epss_medium",
              sc.get("epss_medium_threshold", 0.05) <= f.epss < sc.get("epss_high_threshold", 0.3))
        apply("verified-secret", "verified_secret", f.verified)
        apply("internet-facing", "internet_facing",
              ctx.get("internet_facing") and f.category in {"SAST", "DAST", "SCA", "CONTAINER"})
        apply("fix-available", "fix_available", f.fix_available)
        apply("multi-tool", "confirmed_by_multiple_tools", len(f.confirmed_by) > 1)
        apply("non-prod-path", "non_production_path", in_non_prod(f.file, nonprod))
        apply("dev-dependency", "dev_dependency", f.dev_dependency)
        apply("no-fix", "unfixed", bool(f.cve) and not f.fix_available)

        f.risk_score = round(min(100.0, max(0.0, s)), 1)
        f.risk_factors = factors
        days = sla.get(f.severity)
        if days:
            f.sla_due = (today + timedelta(days=int(days))).isoformat()


def apply_exceptions(findings: list[Finding], exc_path: Path | None) -> tuple[list[dict], list[dict]]:
    """Returns (all_exceptions, expired_exceptions)."""
    if not exc_path or not exc_path.exists():
        return [], []
    doc = yaml.safe_load(exc_path.read_text()) or {}
    entries = doc.get("exceptions", []) or []
    today = date.today()
    expired: list[dict] = []

    for e in entries:
        required = {"id", "reason", "owner", "expires", "approved_by"}
        missing = required - set(e)
        if missing:
            e["_error"] = f"missing required field(s): {', '.join(sorted(missing))}"
            expired.append(e)
            continue
        try:
            exp = datetime.strptime(str(e["expires"]), "%Y-%m-%d").date()
        except ValueError:
            e["_error"] = f"unparseable expiry '{e['expires']}' (want YYYY-MM-DD)"
            expired.append(e)
            continue
        e["_days_left"] = (exp - today).days
        if exp < today:
            e["_error"] = f"expired {(today - exp).days} day(s) ago"
            expired.append(e)
            continue

        scope = str(e.get("scope", "")).strip()
        for f in findings:
            if e["id"] not in (f.cve, f.rule_id):
                continue
            if scope:
                kind, _, value = scope.partition(":")
                if kind == "path" and not fnmatch.fnmatch(normalise_path(f.file), value):
                    continue
                if kind == "package" and value.split("@")[0].lower() != f.package.lower():
                    continue
            f.accepted = True
            f.acceptance = {k: v for k, v in e.items() if not k.startswith("_")}
    return entries, expired


def apply_baseline(findings: list[Finding], baseline_path: Path | None) -> None:
    known: set[str] = set()
    if baseline_path and baseline_path.exists():
        try:
            known = set(json.loads(baseline_path.read_text()).get("fingerprints", []))
        except Exception:
            known = set()
    for f in findings:
        f.status = "existing" if f.fingerprint in known else "new"
    if not known:
        # First run: everything is "new" would be useless noise, so treat the
        # first scan as the baseline itself and report it explicitly.
        for f in findings:
            f.status = "baseline"


# ---------------------------------------------------------------------------
# Optional local LLM triage (Ollama). Advisory only, never up-ranks.
# ---------------------------------------------------------------------------
def llm_triage(findings: list[Finding], policy: dict) -> None:
    cfg = policy.get("llm_triage", {})
    if not cfg.get("enabled"):
        return
    endpoint = cfg.get("endpoint", "http://localhost:11434").rstrip("/")
    model = cfg.get("model", "qwen2.5-coder:7b")
    top = sorted(findings, key=lambda f: -f.risk_score)[: int(cfg.get("max_findings", 50))]
    print(f"  · local LLM triage: {len(top)} finding(s) via {model}")

    for f in top:
        prompt = (
            "You are a senior application security engineer triaging a static analysis "
            "finding. Answer ONLY with JSON: "
            '{"likely_false_positive": true|false, "confidence": 0.0-1.0, "reason": "<=200 chars"}\n\n'
            f"Tool: {f.tool}\nRule: {f.rule_id}\nSeverity: {f.severity}\n"
            f"File: {f.file}:{f.line}\nTitle: {f.title}\nDetail: {f.description[:1200]}"
        )
        try:
            body = json.dumps({"model": model, "prompt": prompt, "stream": False,
                               "options": {"temperature": 0}}).encode()
            req = urllib.request.Request(
                f"{endpoint}/api/generate", data=body,
                headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=90) as r:
                raw = json.loads(r.read()).get("response", "")
            m = re.search(r"\{.*\}", raw, re.S)
            if not m:
                continue
            verdict = json.loads(m.group(0))
        except Exception as exc:
            print(f"    ! LLM triage unavailable ({exc}); continuing without it", file=sys.stderr)
            return
        if verdict.get("likely_false_positive") and float(verdict.get("confidence", 0)) >= 0.8:
            f.triage_note = f"LLM: likely FP ({verdict.get('confidence')}) — {verdict.get('reason','')}"
            if cfg.get("advisory_only", True):
                f.risk_score = round(f.risk_score * 0.7, 1)   # down-rank only
                f.risk_factors.append("llm-down-ranked(x0.7)")


# ---------------------------------------------------------------------------
# Gate
# ---------------------------------------------------------------------------
def effective_gate(policy: dict, ref: str) -> dict:
    gate = dict(policy.get("gate", {}))
    for pattern, override in (gate.get("branch_overrides") or {}).items():
        if fnmatch.fnmatch(ref, pattern):
            gate.update(override)
    return gate


def evaluate_gate(findings: list[Finding], policy: dict, ref: str,
                  expired_exceptions: list[dict]) -> tuple[bool, list[str]]:
    gate = effective_gate(policy, ref)
    always = set(gate.get("always_block", []))
    reasons: list[str] = []

    considered = [f for f in findings if not f.accepted]
    if gate.get("block_on_new_only", True):
        considered = [f for f in considered if f.status == "new"]

    if "expired_exception" in always and expired_exceptions:
        for e in expired_exceptions:
            reasons.append(f"Exception '{e.get('id','?')}' is invalid: {e.get('_error')}")

    if "verified_secret" in always:
        for f in findings:
            if f.verified and not f.accepted:
                reasons.append(f"Verified live credential ({f.rule_id}) at {f.file}:{f.line} — rotate now")

    if "kev_listed_critical" in always:
        for f in considered:
            if f.kev and f.severity == "CRITICAL":
                reasons.append(f"CISA KEV + CRITICAL: {f.cve or f.rule_id} in {f.package or f.file}")

    threshold = float(gate.get("block_above_risk_score", 70))
    over = [f for f in considered if f.risk_score >= threshold]
    if over:
        top = sorted(over, key=lambda f: -f.risk_score)[:5]
        reasons.append(
            f"{len(over)} new finding(s) at or above risk score {threshold:.0f}: "
            + "; ".join(f"{f.rule_id or f.cve} [{f.risk_score}]" for f in top)
        )

    counts = Counter(f.severity for f in considered)
    if counts["CRITICAL"] > int(gate.get("max_new_critical", 0)):
        reasons.append(f"{counts['CRITICAL']} new CRITICAL exceeds the limit of {gate.get('max_new_critical', 0)}")
    if counts["HIGH"] > int(gate.get("max_new_high", 5)):
        reasons.append(f"{counts['HIGH']} new HIGH exceeds the limit of {gate.get('max_new_high', 5)}")

    return (len(reasons) == 0), reasons


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------
def kpis(findings: list[Finding]) -> dict[str, Any]:
    sev = Counter(f.severity for f in findings)
    return {
        "total": len(findings),
        "by_severity": {s: sev.get(s, 0) for s in SEVERITY_ORDER},
        "by_category": dict(Counter(f.category for f in findings)),
        "by_tool": dict(Counter(f.tool for f in findings)),
        "new": sum(1 for f in findings if f.status == "new"),
        "existing": sum(1 for f in findings if f.status == "existing"),
        "accepted": sum(1 for f in findings if f.accepted),
        "kev": sum(1 for f in findings if f.kev),
        "verified_secrets": sum(1 for f in findings if f.verified),
        "fixable": sum(1 for f in findings if f.fix_available),
        "high_epss": sum(1 for f in findings if f.epss >= 0.3),
        "mean_risk": round(sum(f.risk_score for f in findings) / max(1, len(findings)), 1),
    }


def write_markdown(path: Path, findings: list[Finding], k: dict, meta: dict,
                   passed: bool, reasons: list[str], expiring: list[dict]) -> None:
    s = k["by_severity"]
    verdict = "✅ **PASS**" if passed else "❌ **FAIL — merge blocked**"
    lines = [
        "## 🛡️ DevSecOps Security Report",
        "",
        f"{verdict} · `{meta.get('ref','')}` @ `{meta.get('sha','')[:8]}` · "
        f"{meta.get('generated','')}",
        "",
        "| Severity | Critical | High | Medium | Low | Info | **Total** |",
        "|---|---:|---:|---:|---:|---:|---:|",
        f"| Count | {s['CRITICAL']} | {s['HIGH']} | {s['MEDIUM']} | {s['LOW']} | {s['INFO']} | **{k['total']}** |",
        "",
        f"**New this run:** {k['new']} · **Pre-existing:** {k['existing']} · "
        f"**Risk-accepted:** {k['accepted']} · **Mean risk score:** {k['mean_risk']}",
        "",
        f"**Actively exploited (CISA KEV):** {k['kev']} · "
        f"**EPSS ≥ 0.30:** {k['high_epss']} · "
        f"**Verified live secrets:** {k['verified_secrets']} · "
        f"**Fix available:** {k['fixable']}",
        "",
    ]
    if not passed:
        lines += ["### Why the gate failed", ""] + [f"- {r}" for r in reasons] + [""]

    actionable = sorted(
        [f for f in findings if not f.accepted and f.status != "existing"],
        key=lambda f: -f.risk_score)[:15]
    if actionable:
        lines += [
            "<details open><summary><b>Top findings to fix first</b></summary>", "",
            "| Risk | Sev | Category | Finding | Location | Fix |",
            "|---:|---|---|---|---|---|",
        ]
        for f in actionable:
            loc = f"`{f.file}:{f.line}`" if f.file else (f"`{f.package}@{f.installed_version}`" if f.package else "—")
            fix = f"→ `{f.fixed_version}`" if f.fixed_version else (f.remediation[:60] + "…" if f.remediation else "—")
            flags = ("🔥KEV " if f.kev else "") + (f"EPSS {f.epss:.2f}" if f.epss >= 0.05 else "")
            lines.append(
                f"| **{f.risk_score}** {flags} | {f.severity} | {f.category} | "
                f"{f.title[:70].replace('|', '\\|')} | {loc} | {fix.replace('|', '\\|')} |")
        lines += ["", "</details>", ""]

    if expiring:
        lines += ["### ⏳ Risk acceptances expiring within 30 days", ""]
        lines += [f"- `{e['id']}` — owner {e.get('owner')} — {e.get('_days_left')} day(s) left "
                  f"({e.get('ticket','no ticket')})" for e in expiring]
        lines.append("")

    lines += [
        "---",
        f"📄 Full **PDF** and **Excel** reports are attached to "
        f"[this workflow run]({meta.get('run_url','#')}) under *Artifacts → security-report*.",
        "",
        "<sub>Generated by `tools/secreport.py` · Semgrep · Trivy · Grype · OSV · Gitleaks · "
        "TruffleHog · Checkov · Conftest/OPA · Hadolint · Dockle · ZAP · zizmor · "
        "enriched with CISA KEV + FIRST EPSS. All open source.</sub>",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def write_sarif(path: Path, findings: list[Finding]) -> None:
    level = {"CRITICAL": "error", "HIGH": "error", "MEDIUM": "warning",
             "LOW": "note", "INFO": "note"}
    rules, seen = [], set()
    results = []
    for f in findings:
        rid = f"{f.tool}:{f.rule_id}"[:200]
        if rid not in seen:
            seen.add(rid)
            rules.append({
                "id": rid,
                "name": re.sub(r"\W+", "", f.rule_id)[:100] or "finding",
                "shortDescription": {"text": f.title[:200]},
                "fullDescription": {"text": (f.description or f.title)[:900]},
                "help": {"text": f.remediation or f.description or f.title},
                "properties": {
                    "security-severity": str({"CRITICAL": 9.5, "HIGH": 7.5,
                                              "MEDIUM": 5.0, "LOW": 3.0, "INFO": 1.0}[f.severity]),
                    "tags": [f.category, f.tool] + (["cisa-kev"] if f.kev else []),
                },
            })
        results.append({
            "ruleId": rid,
            "level": level[f.severity],
            "message": {"text": f"[risk {f.risk_score}] {f.title}"
                                + (f" — fix: {f.fixed_version}" if f.fixed_version else "")},
            "partialFingerprints": {"secreport/v1": f.fingerprint},
            "locations": [{"physicalLocation": {
                "artifactLocation": {"uri": f.file or "UNKNOWN"},
                "region": {"startLine": max(1, f.line)},
            }}],
        })
    path.write_text(json.dumps({
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [{
            "tool": {"driver": {"name": "secreport", "version": "1.0",
                                "informationUri": "https://github.com/",
                                "rules": rules}},
            "results": results,
        }],
    }, indent=1), encoding="utf-8")


def write_xlsx(path: Path, findings: list[Finding], k: dict, meta: dict,
               sbom: list[dict], exceptions: list[dict], policy: dict) -> None:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.table import Table, TableStyleInfo

    ARIAL = "Arial"
    NAVY = "1F3864"
    HDR = PatternFill("solid", fgColor=NAVY)
    HDR_FONT = Font(name=ARIAL, bold=True, color="FFFFFF", size=10)
    TITLE = Font(name=ARIAL, bold=True, size=16, color=NAVY)
    SUB = Font(name=ARIAL, size=9, color="595959")
    BOLD = Font(name=ARIAL, bold=True, size=10)
    BODY = Font(name=ARIAL, size=10)
    thin = Side(style="thin", color="D9D9D9")
    BOX = Border(left=thin, right=thin, top=thin, bottom=thin)
    SEV_FILL = {"CRITICAL": "C00000", "HIGH": "E36C0A", "MEDIUM": "BF9000",
                "LOW": "548235", "INFO": "808080"}

    wb = Workbook()

    # ---------------------------------------------------------------- Findings
    ws = wb.create_sheet("Findings")
    headers = ["Risk Score", "Severity", "Status", "Accepted", "Category", "Tool",
               "Rule ID", "Title", "CVE", "CWE", "KEV", "EPSS", "File", "Line",
               "Package", "Installed", "Fixed Version", "Fix Available",
               "SLA Due", "Confirmed By", "Remediation", "Fingerprint", "Risk Factors"]
    ws.append(headers)
    rows = sorted(findings, key=lambda f: -f.risk_score)
    for f in rows:
        ws.append([
            f.risk_score, f.severity, f.status, "YES" if f.accepted else "NO",
            f.category, f.tool, f.rule_id, f.title, f.cve, f.cwe,
            "YES" if f.kev else "NO", round(f.epss, 4), f.file, f.line,
            f.package, f.installed_version, f.fixed_version,
            "YES" if f.fix_available else "NO", f.sla_due,
            ", ".join(f.confirmed_by), (f.remediation or "")[:500], f.fingerprint,
            " ".join(f.risk_factors),
        ])
    n = len(rows)
    last = max(2, n + 1)
    for c in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=c)
        cell.fill, cell.font, cell.border = HDR, HDR_FONT, BOX
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    for r in range(2, n + 2):
        for c in range(1, len(headers) + 1):
            cell = ws.cell(row=r, column=c)
            cell.font, cell.border = BODY, BOX
            cell.alignment = Alignment(vertical="top", wrap_text=(c in (8, 21, 23)))
        sv = ws.cell(row=r, column=2)
        sv.font = Font(name=ARIAL, bold=True, size=10, color=SEV_FILL.get(sv.value, "000000"))
    widths = [11, 10, 10, 10, 14, 12, 26, 52, 17, 12, 6, 8, 34, 7, 20, 13, 15, 8, 12, 18, 60, 18, 40]
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(headers))}{last}"
    F = "Findings"

    # -------------------------------------------------------- Executive Summary
    es = wb.active
    es.title = "Executive Summary"
    es["A1"] = "Application Security Report"
    es["A1"].font = TITLE
    es["A2"] = (f"Repository {meta.get('repo','-')} · branch {meta.get('ref','-')} · "
                f"commit {meta.get('sha','')[:12]} · generated {meta.get('generated','')}")
    es["A2"].font = SUB
    es["A3"] = ("Every figure below is a live formula over the Findings sheet — filter or edit "
                "that sheet and these recalculate.")
    es["A3"].font = SUB

    def block(row: int, title: str, pairs: list[tuple[str, str]]) -> int:
        es.cell(row=row, column=1, value=title).font = Font(name=ARIAL, bold=True, size=12, color=NAVY)
        row += 1
        for label, formula in pairs:
            lc = es.cell(row=row, column=1, value=label); lc.font = BODY; lc.border = BOX
            vc = es.cell(row=row, column=2, value=formula); vc.font = BOLD; vc.border = BOX
            vc.alignment = Alignment(horizontal="center")
            row += 1
        return row + 1

    r = 5
    r = block(r, "Posture by severity", [
        (s, f'=COUNTIF({F}!$B$2:$B${last},"{s}")') for s in SEVERITY_ORDER
    ] + [("TOTAL", f"=COUNTA({F}!$A$2:$A${last})")])

    r = block(r, "Triage state", [
        ("New this run", f'=COUNTIF({F}!$C$2:$C${last},"new")'),
        ("Pre-existing", f'=COUNTIF({F}!$C$2:$C${last},"existing")'),
        ("Risk-accepted (suppressed)", f'=COUNTIF({F}!$D$2:$D${last},"YES")'),
        ("Fix available today", f'=COUNTIF({F}!$R$2:$R${last},"YES")'),
        ("Mean risk score", f"=IFERROR(ROUND(AVERAGE({F}!$A$2:$A${last}),1),0)"),
        ("Highest risk score", f"=IFERROR(MAX({F}!$A$2:$A${last}),0)"),
    ])

    r = block(r, "Exploitation intelligence", [
        ("On CISA KEV (exploited in the wild)", f'=COUNTIF({F}!$K$2:$K${last},"YES")'),
        ("EPSS >= 0.30 (high exploit probability)", f'=COUNTIF({F}!$L$2:$L${last},">=0.3")'),
        ("EPSS >= 0.05", f'=COUNTIF({F}!$L$2:$L${last},">=0.05")'),
        ("KEV + no fix available",
         f'=COUNTIFS({F}!$K$2:$K${last},"YES",{F}!$R$2:$R${last},"NO")'),
    ])

    r = block(r, "Immediate action queue (new, unaccepted, risk >= 70)", [
        ("Critical",
         f'=COUNTIFS({F}!$B$2:$B${last},"CRITICAL",{F}!$C$2:$C${last},"new",{F}!$D$2:$D${last},"NO")'),
        ("High",
         f'=COUNTIFS({F}!$B$2:$B${last},"HIGH",{F}!$C$2:$C${last},"new",{F}!$D$2:$D${last},"NO")'),
        ("Risk score >= 70",
         f'=COUNTIFS({F}!$A$2:$A${last},">=70",{F}!$D$2:$D${last},"NO")'),
    ])

    es.cell(row=r, column=1, value="Breakdown by category").font = Font(name=ARIAL, bold=True, size=12, color=NAVY)
    r += 1
    es.cell(row=r, column=1, value="Category").font = HDR_FONT
    es.cell(row=r, column=1).fill = HDR
    for j, s in enumerate(SEVERITY_ORDER + ["Total"], start=2):
        c = es.cell(row=r, column=j, value=s); c.font, c.fill = HDR_FONT, HDR
        c.alignment = Alignment(horizontal="center")
    hdr_row = r
    r += 1
    for cat in CATEGORIES:
        es.cell(row=r, column=1, value=cat).font = BODY
        es.cell(row=r, column=1).border = BOX
        for j, s in enumerate(SEVERITY_ORDER, start=2):
            c = es.cell(row=r, column=j,
                        value=f'=COUNTIFS({F}!$E$2:$E${last},$A{r},{F}!$B$2:$B${last},{get_column_letter(j)}${hdr_row})')
            c.font, c.border = BODY, BOX
            c.alignment = Alignment(horizontal="center")
        t = es.cell(row=r, column=7, value=f'=SUM(B{r}:F{r})')
        t.font, t.border = BOLD, BOX
        t.alignment = Alignment(horizontal="center")
        r += 1

    es.column_dimensions["A"].width = 46
    for col in "BCDEFG":
        es.column_dimensions[col].width = 13

    # ------------------------------------------------------------------ By Tool
    bt = wb.create_sheet("Coverage by Tool")
    bt.append(["Tool", "Category", "Findings", "Critical", "High", "Medium", "Low", "Info"])
    for c in range(1, 9):
        cell = bt.cell(row=1, column=c); cell.fill, cell.font, cell.border = HDR, HDR_FONT, BOX
    tools = sorted({f.tool for f in findings}) or ["(no findings)"]
    for i, t in enumerate(tools, start=2):
        cat = next((f.category for f in findings if f.tool == t), "")
        bt.cell(row=i, column=1, value=t).font = BODY
        bt.cell(row=i, column=2, value=cat).font = BODY
        bt.cell(row=i, column=3, value=f'=COUNTIF({F}!$F$2:$F${last},$A{i})').font = BODY
        for j, s in enumerate(SEVERITY_ORDER, start=4):
            bt.cell(row=i, column=j,
                    value=f'=COUNTIFS({F}!$F$2:$F${last},$A{i},{F}!$B$2:$B${last},"{s}")').font = BODY
        for c in range(1, 9):
            bt.cell(row=i, column=c).border = BOX
    bt.column_dimensions["A"].width = 22
    bt.column_dimensions["B"].width = 18
    for col in "CDEFGH":
        bt.column_dimensions[col].width = 11

    # -------------------------------------------------------------- SLA tracker
    sl = wb.create_sheet("SLA Tracker")
    sl["A1"] = "Remediation SLAs (from security/risk-policy.yaml, days from detection)"
    sl["A1"].font = Font(name=ARIAL, bold=True, size=12, color=NAVY)
    sl.append([])
    sl.append(["Severity", "SLA (days)", "Open findings", "Due date"])
    for c in range(1, 5):
        cell = sl.cell(row=3, column=c); cell.fill, cell.font = HDR, HDR_FONT
    sla = policy.get("sla_days", {})
    for i, s in enumerate(["CRITICAL", "HIGH", "MEDIUM", "LOW"], start=4):
        sl.cell(row=i, column=1, value=s).font = BODY
        sl.cell(row=i, column=2, value=sla.get(s, "")).font = BODY
        sl.cell(row=i, column=3,
                value=f'=COUNTIFS({F}!$B$2:$B${last},$A{i},{F}!$D$2:$D${last},"NO")').font = BODY
        due = next((f.sla_due for f in findings if f.severity == s and f.sla_due), "")
        sl.cell(row=i, column=4, value=due).font = BODY
    for col, w in zip("ABCD", (16, 14, 16, 14)):
        sl.column_dimensions[col].width = w

    # ------------------------------------------------------------------ SBOM
    sb = wb.create_sheet("SBOM")
    sb.append(["Component", "Version", "Type", "License", "Package URL", "Source"])
    for c in range(1, 7):
        cell = sb.cell(row=1, column=c); cell.fill, cell.font, cell.border = HDR, HDR_FONT, BOX
    for comp in sbom:
        sb.append([comp["name"], comp["version"], comp["type"], comp["license"],
                   comp["purl"], comp["source"]])
    for i in range(2, len(sbom) + 2):
        for c in range(1, 7):
            sb.cell(row=i, column=c).font = BODY
    for col, w in zip("ABCDEF", (38, 16, 14, 22, 62, 22)):
        sb.column_dimensions[col].width = w
    sb.freeze_panes = "A2"
    if sbom:
        sb.auto_filter.ref = f"A1:F{len(sbom) + 1}"

    # ------------------------------------------------------------ Exceptions
    ex = wb.create_sheet("Risk Acceptances")
    ex["A1"] = "Risk acceptance register (security/exceptions.yaml)"
    ex["A1"].font = Font(name=ARIAL, bold=True, size=12, color=NAVY)
    ex["A2"] = ("Every acceptance is time-boxed. An expired entry fails the pipeline by design, "
                "so a suppression cannot quietly become permanent.")
    ex["A2"].font = SUB
    ex.append([])
    ex.append(["ID", "Scope", "Owner", "Approved By", "Expires", "Days Left", "Ticket", "Reason", "Status"])
    for c in range(1, 10):
        cell = ex.cell(row=4, column=c); cell.fill, cell.font, cell.border = HDR, HDR_FONT, BOX
    for e in exceptions:
        ex.append([e.get("id", ""), e.get("scope", ""), e.get("owner", ""),
                   e.get("approved_by", ""), str(e.get("expires", "")),
                   e.get("_days_left", ""), e.get("ticket", ""),
                   (e.get("reason", "") or "").strip()[:400],
                   e.get("_error", "valid")])
    for i in range(5, len(exceptions) + 5):
        for c in range(1, 10):
            cell = ex.cell(row=i, column=c)
            cell.font, cell.border = BODY, BOX
            cell.alignment = Alignment(vertical="top", wrap_text=(c == 8))
    for col, w in zip("ABCDEFGHI", (24, 28, 20, 20, 13, 11, 12, 60, 26)):
        ex.column_dimensions[col].width = w

    # ------------------------------------------------------------- Methodology
    me = wb.create_sheet("Methodology")
    me["A1"] = "Scope, tooling and scoring methodology"
    me["A1"].font = Font(name=ARIAL, bold=True, size=12, color=NAVY)
    me.append([])
    me.append(["Control", "Tool (all open source)", "Licence", "What it catches"])
    for c in range(1, 5):
        cell = me.cell(row=3, column=c); cell.fill, cell.font, cell.border = HDR, HDR_FONT, BOX
    for row in METHODOLOGY_ROWS:
        me.append(list(row))
    for i in range(4, 4 + len(METHODOLOGY_ROWS)):
        for c in range(1, 5):
            cell = me.cell(row=i, column=c)
            cell.font, cell.border = BODY, BOX
            cell.alignment = Alignment(vertical="top", wrap_text=True)
    for col, w in zip("ABCD", (26, 30, 16, 74)):
        me.column_dimensions[col].width = w

    r = 4 + len(METHODOLOGY_ROWS) + 2
    me.cell(row=r, column=1, value="Risk score").font = Font(name=ARIAL, bold=True, size=11, color=NAVY)
    for text in [
        "risk = base(severity) × KEV × EPSS × verified-secret × internet-facing × fix-available "
        "× multi-tool-confirmation × non-production-path × dev-dependency, clamped to 0-100.",
        "CISA KEV = the vulnerability is being exploited in the wild right now (free, public catalog).",
        "EPSS = FIRST's probability of exploitation in the next 30 days (free, public, daily refresh).",
        "Findings on test/doc/example paths are damped by 65%, which is where most of the noise lives.",
        "A finding reported by two independent engines gets a confidence uplift rather than a duplicate row.",
    ]:
        r += 1
        c = me.cell(row=r, column=1, value=text)
        c.font, c.alignment = BODY, Alignment(wrap_text=True, vertical="top")
        me.merge_cells(start_row=r, start_column=1, end_row=r, end_column=4)
        me.row_dimensions[r].height = 30

    wb.save(path)


METHODOLOGY_ROWS = [
    ("Secrets", "Gitleaks + TruffleHog", "MIT / AGPL-3.0",
     "Hardcoded credentials across the full git history. TruffleHog verifies against the "
     "provider API, so a hit is a live key, not a regex guess."),
    ("SAST", "Semgrep OSS (+ CodeQL on public repos)", "LGPL-2.1 / MIT",
     "Injection, XSS, deserialisation, path traversal, crypto misuse, plus organisation-specific "
     "rules in .config/semgrep/custom.yaml."),
    ("SCA", "Trivy + Grype + OSV-Scanner", "Apache-2.0 / Apache-2.0 / Apache-2.0",
     "Known CVEs in direct and transitive dependencies across npm, pip, Go, Maven, Gradle, "
     "NuGet, Cargo, Composer, RubyGems."),
    ("SBOM", "Syft (CycloneDX + SPDX)", "Apache-2.0",
     "Machine-readable inventory of everything shipped. Required by EO 14028, the EU CRA and "
     "most enterprise vendor questionnaires."),
    ("IaC", "Checkov + Trivy config", "Apache-2.0",
     "Terraform, CloudFormation, Kubernetes, Helm, ARM and Dockerfile misconfiguration."),
    ("Policy as code", "Conftest / OPA (Rego)", "Apache-2.0",
     "Organisational guardrails no vendor ships: approved registries, mandatory tags, no :latest, "
     "no wildcard IAM, resource limits."),
    ("Container", "Hadolint + Dockle + Trivy image", "GPL-3.0 / Apache-2.0 / Apache-2.0",
     "Dockerfile hygiene, CIS Docker Benchmark controls, OS and language package CVEs in the "
     "actual shipped image."),
    ("DAST", "OWASP ZAP + Nuclei", "Apache-2.0 / MIT",
     "Runtime issues invisible to static analysis: missing security headers, CSRF, reflected "
     "injection, exposed admin paths."),
    ("CI supply chain", "zizmor + actionlint + OpenSSF Scorecard", "MIT / MIT / Apache-2.0",
     "The pipeline as an attack surface: script injection, pwn-requests, over-permissioned "
     "tokens, unpinned third-party actions, artifact credential leakage."),
    ("Artifact integrity", "Sigstore cosign + SLSA provenance", "Apache-2.0",
     "Keyless signing and build provenance so consumers can prove where the artifact came from."),
    ("Exploit intelligence", "CISA KEV + FIRST EPSS", "Public domain / free",
     "Turns a severity label into a real-world priority."),
]


def write_pdf(path: Path, findings: list[Finding], k: dict, meta: dict,
              exceptions: list[dict], policy: dict, passed: bool, reasons: list[str],
              chart_dir: Path) -> None:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (BaseDocTemplate, Frame, Image, KeepTogether,
                                    PageBreak, PageTemplate, Paragraph, Spacer, Table,
                                    TableStyle)

    NAVY = colors.HexColor("#1F3864")
    ACCENT = colors.HexColor("#2E74B5")
    GREY = colors.HexColor("#595959")
    LIGHT = colors.HexColor("#F2F5FA")
    SEVHEX = {"CRITICAL": "#C00000", "HIGH": "#E36C0A", "MEDIUM": "#BF9000",
              "LOW": "#548235", "INFO": "#808080"}
    SEVC = {"CRITICAL": colors.HexColor("#C00000"), "HIGH": colors.HexColor("#E36C0A"),
            "MEDIUM": colors.HexColor("#BF9000"), "LOW": colors.HexColor("#548235"),
            "INFO": colors.HexColor("#808080")}

    ss = getSampleStyleSheet()
    H1 = ParagraphStyle("H1", parent=ss["Heading1"], fontName="Helvetica-Bold",
                        fontSize=16, textColor=NAVY, spaceAfter=8, spaceBefore=4)
    H2 = ParagraphStyle("H2", parent=ss["Heading2"], fontName="Helvetica-Bold",
                        fontSize=12, textColor=ACCENT, spaceAfter=5, spaceBefore=10)
    BODY = ParagraphStyle("BODY", parent=ss["BodyText"], fontName="Helvetica",
                          fontSize=9.2, leading=13.2, alignment=TA_LEFT, spaceAfter=5)
    SMALL = ParagraphStyle("SMALL", parent=BODY, fontSize=7.6, leading=9.6, textColor=GREY)
    CELL = ParagraphStyle("CELL", parent=BODY, fontSize=7.5, leading=9.3, spaceAfter=0)
    CELLB = ParagraphStyle("CELLB", parent=CELL, fontName="Helvetica-Bold")

    def header_footer(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(NAVY)
        canvas.rect(0, A4[1] - 14 * mm, A4[0], 14 * mm, stroke=0, fill=1)
        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica-Bold", 9)
        canvas.drawString(18 * mm, A4[1] - 9.4 * mm, "DevSecOps Security Report")
        canvas.setFont("Helvetica", 8)
        canvas.drawRightString(A4[0] - 18 * mm, A4[1] - 9.4 * mm,
                               f"{meta.get('repo','')} · {meta.get('ref','')}")
        canvas.setFillColor(GREY)
        canvas.setFont("Helvetica", 7.5)
        canvas.drawString(18 * mm, 10 * mm, "CONFIDENTIAL — internal security assessment")
        canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {doc.page}")
        canvas.setStrokeColor(colors.HexColor("#D9D9D9"))
        canvas.line(18 * mm, 13 * mm, A4[0] - 18 * mm, 13 * mm)
        canvas.restoreState()

    doc = BaseDocTemplate(str(path), pagesize=A4,
                          leftMargin=18 * mm, rightMargin=18 * mm,
                          topMargin=20 * mm, bottomMargin=16 * mm,
                          title="DevSecOps Security Report", author="secreport")
    frame = Frame(doc.leftMargin, doc.bottomMargin,
                  doc.width, doc.height, id="body")
    doc.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=header_footer)])

    story: list[Any] = []
    s = k["by_severity"]

    # ---- verdict banner
    banner_text = ("PASS — no blocking security findings"
                   if passed else "FAIL — merge blocked by security policy")
    banner = Table([[Paragraph(f"<font color='white'><b>{banner_text}</b></font>", BODY)]],
                   colWidths=[doc.width])
    banner.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1),
         colors.HexColor("#548235") if passed else colors.HexColor("#C00000")),
        ("LEFTPADDING", (0, 0), (-1, -1), 10), ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))

    story += [
        Paragraph("Application Security Assessment", H1),
        Paragraph(
            f"<b>Repository</b> {meta.get('repo','-')} &nbsp;|&nbsp; "
            f"<b>Branch</b> {meta.get('ref','-')} &nbsp;|&nbsp; "
            f"<b>Commit</b> {meta.get('sha','')[:12]} &nbsp;|&nbsp; "
            f"<b>Generated</b> {meta.get('generated','')}", SMALL),
        Spacer(1, 6), banner, Spacer(1, 10),
    ]

    # ---- KPI strip
    kpi_rows = [[
        Paragraph(f"<font size=15 color='#C00000'><b>{s['CRITICAL']}</b></font><br/>"
                  "<font size=7>CRITICAL</font>", CELL),
        Paragraph(f"<font size=15 color='#E36C0A'><b>{s['HIGH']}</b></font><br/>"
                  "<font size=7>HIGH</font>", CELL),
        Paragraph(f"<font size=15 color='#BF9000'><b>{s['MEDIUM']}</b></font><br/>"
                  "<font size=7>MEDIUM</font>", CELL),
        Paragraph(f"<font size=15 color='#1F3864'><b>{k['new']}</b></font><br/>"
                  "<font size=7>NEW THIS RUN</font>", CELL),
        Paragraph(f"<font size=15 color='#C00000'><b>{k['kev']}</b></font><br/>"
                  "<font size=7>CISA KEV</font>", CELL),
        Paragraph(f"<font size=15 color='#548235'><b>{k['fixable']}</b></font><br/>"
                  "<font size=7>FIX AVAILABLE</font>", CELL),
    ]]
    kt = Table(kpi_rows, colWidths=[doc.width / 6.0] * 6)
    kt.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT),
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#D9D9D9")),
        ("INNERGRID", (0, 0), (-1, -1), 0.6, colors.white),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story += [kt, Spacer(1, 12)]

    # ---- executive summary prose
    story.append(Paragraph("Executive summary", H2))
    top_cat = max(k["by_category"].items(), key=lambda x: x[1])[0] if k["by_category"] else "n/a"
    story.append(Paragraph(
        f"This assessment consolidates {len(k['by_tool'])} independent open source scanners across "
        f"{len(k['by_category'])} control domains into {k['total']} de-duplicated findings. "
        f"{k['new']} are new in this run and {k['existing']} pre-date it; only new findings can block a merge, "
        f"so historical debt is tracked and burned down rather than punishing unrelated changes. "
        f"{k['kev']} finding(s) map to vulnerabilities on the CISA Known Exploited Vulnerabilities catalog "
        f"and {k['high_epss']} carry an EPSS score above 0.30, meaning exploitation in the next 30 days is "
        f"materially likely. {k['fixable']} finding(s) already have a published fix, which makes them the "
        f"cheapest risk reduction available today. The largest concentration of issues is in the "
        f"<b>{top_cat}</b> domain. Mean risk score across all findings is {k['mean_risk']}/100.", BODY))
    if not passed:
        story.append(Paragraph("Why this build is blocked", H2))
        for reason in reasons:
            story.append(Paragraph(f"• {reason}", BODY))

    # ---- charts
    charts = build_charts(findings, k, chart_dir)
    if charts:
        story.append(Spacer(1, 6))
        imgs = [Image(str(c), width=doc.width / 2 - 4, height=(doc.width / 2 - 4) * 0.62)
                for c in charts[:2]]
        if len(imgs) == 2:
            ct = Table([imgs], colWidths=[doc.width / 2, doc.width / 2])
            ct.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                                    ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
            story.append(ct)
        else:
            story.append(imgs[0])

    story.append(PageBreak())

    # ---- priority findings table
    story.append(Paragraph("Priority remediation queue", H1))
    story.append(Paragraph(
        "Ordered by contextual risk score, not raw severity. A MEDIUM CVE that is actively exploited "
        "outranks a CRITICAL in a test fixture — that ordering is the entire point of the scoring model.",
        SMALL))
    story.append(Spacer(1, 6))

    head = ["#", "Risk", "Sev", "Domain", "Finding", "Location", "Remediation"]
    data = [[Paragraph(f"<b>{h}</b>", CELLB) for h in head]]
    queue = sorted([f for f in findings if not f.accepted], key=lambda f: -f.risk_score)[:25]
    for i, f in enumerate(queue, start=1):
        loc = f"{f.file}:{f.line}" if f.file else (f"{f.package} {f.installed_version}" if f.package else "—")
        fix = (f"Upgrade to {f.fixed_version}" if f.fixed_version
               else (f.remediation[:150] or "Review and remediate manually"))
        flag = " <font color='#C00000'><b>[KEV]</b></font>" if f.kev else ""
        data.append([
            Paragraph(str(i), CELL),
            Paragraph(f"<b>{f.risk_score:g}</b>", CELL),
            Paragraph(f"<font color='{SEVHEX[f.severity]}'><b>{f.severity[:4]}</b></font>", CELL),
            Paragraph(f.category.replace("_", " "), CELL),
            Paragraph(f"{esc(f.title[:110])}{flag}<br/><font size=6 color='#808080'>"
                      f"{esc(f.rule_id[:60])}{' · ' + f.cve if f.cve else ''}"
                      f"{f' · EPSS {f.epss:.2f}' if f.epss >= 0.01 else ''}</font>", CELL),
            Paragraph(f"<font size=6.5>{esc(loc[-58:])}</font>", CELL),
            Paragraph(esc(fix[:150]), CELL),
        ])
    if len(data) == 1:
        data.append([Paragraph("No unaccepted findings.", CELL)] + [Paragraph("", CELL)] * 6)

    t = Table(data, colWidths=[8 * mm, 12 * mm, 12 * mm, 20 * mm, 58 * mm, 30 * mm, 34 * mm],
              repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D9D9D9")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
        ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story += [t, Spacer(1, 8)]
    story.append(Paragraph(
        f"Showing the top {len(queue)} of {sum(1 for f in findings if not f.accepted)} unaccepted findings. "
        "The complete, filterable set is in the accompanying Excel workbook (Findings sheet).", SMALL))

    story.append(PageBreak())

    # ---- control coverage
    story.append(Paragraph("Control coverage and methodology", H1))
    story.append(Paragraph(
        "Every tool below is open source with no licence fee, no account and no usage cap. "
        "Overlap between engines is deliberate: agreement between two independent tools raises "
        "confidence, and the aggregator de-duplicates rather than double-counting.", BODY))
    mrows = [[Paragraph(f"<b>{h}</b>", CELLB) for h in ("Control", "Tooling", "Licence", "Coverage")]]
    for row in METHODOLOGY_ROWS:
        mrows.append([Paragraph(esc(row[0]), CELL), Paragraph(esc(row[1]), CELL),
                      Paragraph(esc(row[2]), CELL), Paragraph(esc(row[3]), CELL)])
    mt = Table(mrows, colWidths=[26 * mm, 36 * mm, 24 * mm, 88 * mm], repeatRows=1)
    mt.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D9D9D9")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story += [Spacer(1, 4), mt, Spacer(1, 10)]

    # ---- compliance mapping
    story.append(Paragraph("Framework alignment", H2))
    crows = [[Paragraph(f"<b>{h}</b>", CELLB) for h in ("Framework", "Requirement", "How this pipeline satisfies it")]]
    for fw, req, how in COMPLIANCE_ROWS:
        crows.append([Paragraph(esc(fw), CELL), Paragraph(esc(req), CELL), Paragraph(esc(how), CELL)])
    ct2 = Table(crows, colWidths=[34 * mm, 48 * mm, 92 * mm], repeatRows=1)
    ct2.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D9D9D9")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(ct2)

    # ---- exceptions
    if exceptions:
        story += [Spacer(1, 10), Paragraph("Risk acceptance register", H2),
                  Paragraph("Time-boxed by design. An expired acceptance fails the pipeline, "
                            "so a suppression cannot silently become permanent.", SMALL),
                  Spacer(1, 4)]
        erows = [[Paragraph(f"<b>{h}</b>", CELLB)
                  for h in ("ID", "Owner", "Expires", "Days left", "Status", "Reason")]]
        for e in exceptions:
            erows.append([
                Paragraph(esc(str(e.get("id", ""))), CELL),
                Paragraph(esc(str(e.get("owner", ""))), CELL),
                Paragraph(esc(str(e.get("expires", ""))), CELL),
                Paragraph(str(e.get("_days_left", "—")), CELL),
                Paragraph(esc(str(e.get("_error", "valid"))), CELL),
                Paragraph(esc((e.get("reason", "") or "").strip()[:220]), CELL),
            ])
        et = Table(erows, colWidths=[28 * mm, 26 * mm, 20 * mm, 16 * mm, 24 * mm, 60 * mm],
                   repeatRows=1)
        et.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D9D9D9")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(et)

    story += [
        Spacer(1, 12),
        Paragraph(
            f"Evidence for this report — raw SARIF, JSON, SBOM (CycloneDX + SPDX) and the "
            f"consolidated dataset — is retained with the workflow run at "
            f"{esc(meta.get('run_url','n/a'))}. Report generated by tools/secreport.py.", SMALL),
    ]
    doc.build(story)


def esc(text: str) -> str:
    return (str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


COMPLIANCE_ROWS = [
    ("NIST SSDF (SP 800-218)", "PW.7 / PW.8 — review and test code",
     "Semgrep and CodeQL on every pull request; DAST against an ephemeral instance of the real image."),
    ("NIST SSDF (SP 800-218)", "PW.4 — reuse secure software",
     "Trivy, Grype and OSV-Scanner on all direct and transitive dependencies; Dependabot for continuous updates."),
    ("NIST SSDF (SP 800-218)", "PS.1 / PS.2 — protect and verify software",
     "Cosign keyless signing and cryptographic verification of every released artifact."),
    ("SLSA v1.0", "Build Level 3 — provenance",
     "GitHub artifact attestations produce signed, non-falsifiable provenance for each build."),
    ("OWASP SAMM v2", "Implementation → Secure Build",
     "Automated security gates in CI with a documented, versioned risk policy."),
    ("OWASP ASVS 4.0", "V14 — configuration",
     "Checkov, Trivy config, Hadolint, Dockle and organisational Rego policy on all IaC and images."),
    ("EO 14028 / EU CRA", "SBOM delivery",
     "CycloneDX and SPDX SBOMs generated per build, attested and retained for 365 days."),
    ("PCI DSS v4.0", "Req. 6.3.2 — inventory of components",
     "The SBOM sheet in the Excel workbook is a per-release component inventory with licences."),
    ("ISO 27001:2022", "A.8.28 — secure coding",
     "Pre-commit hooks, mandatory PR scanning, and an auditable time-boxed exception register."),
]


def build_charts(findings: list[Finding], k: dict, out_dir: Path) -> list[Path]:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return []
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    colours = {"CRITICAL": "#C00000", "HIGH": "#E36C0A", "MEDIUM": "#BF9000",
               "LOW": "#548235", "INFO": "#808080"}

    # severity donut
    s = k["by_severity"]
    labels = [x for x in SEVERITY_ORDER if s[x] > 0]
    if labels:
        fig, ax = plt.subplots(figsize=(4.2, 2.6), dpi=200)
        vals = [s[x] for x in labels]
        wedges, _, autotexts = ax.pie(
            vals, colors=[colours[x] for x in labels], startangle=90,
            wedgeprops=dict(width=0.42, edgecolor="white", linewidth=1.4),
            autopct=lambda p: f"{p*sum(vals)/100:.0f}" if p > 4 else "",
            pctdistance=0.79, textprops=dict(color="white", fontsize=7, weight="bold"))
        ax.legend(wedges, [f"{x.title()} ({s[x]})" for x in labels],
                  loc="center left", bbox_to_anchor=(0.98, 0.5), frameon=False, fontsize=7)
        ax.set_title("Findings by severity", fontsize=9, color="#1F3864", weight="bold")
        ax.text(0, 0, str(k["total"]), ha="center", va="center", fontsize=15,
                weight="bold", color="#1F3864")
        fig.tight_layout()
        p = out_dir / "chart_severity.png"
        fig.savefig(p, transparent=True); plt.close(fig)
        paths.append(p)

    # category stacked bar
    cats = [c for c in CATEGORIES if k["by_category"].get(c)]
    if cats:
        fig, ax = plt.subplots(figsize=(4.6, 2.6), dpi=200)
        bottom = [0] * len(cats)
        for sev in SEVERITY_ORDER:
            vals = [sum(1 for f in findings if f.category == c and f.severity == sev) for c in cats]
            if not any(vals):
                continue
            ax.barh(cats, vals, left=bottom, color=colours[sev], label=sev.title(), height=0.62)
            bottom = [b + v for b, v in zip(bottom, vals)]
        ax.set_title("Findings by control domain", fontsize=9, color="#1F3864", weight="bold")
        ax.tick_params(labelsize=7)
        ax.set_yticks(range(len(cats)))
        ax.set_yticklabels([c.replace("_", " ").title() for c in cats], fontsize=7)
        ax.legend(fontsize=6, frameon=False, ncol=3, loc="lower right")
        for spine in ("top", "right"):
            ax.spines[spine].set_visible(False)
        ax.grid(axis="x", alpha=0.25, linewidth=0.5)
        fig.tight_layout()
        p = out_dir / "chart_category.png"
        fig.savefig(p, transparent=True); plt.close(fig)
        paths.append(p)
    return paths


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def cmd_run(args: argparse.Namespace) -> int:
    inp, out = Path(args.input), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    cache = Path(".secreport-cache"); cache.mkdir(exist_ok=True)

    policy = yaml.safe_load(Path(args.policy).read_text()) if Path(args.policy).exists() else {}

    print("→ collecting scanner output")
    findings = collect(inp)
    print(f"→ {len(findings)} raw findings")

    findings = dedupe(findings)
    print(f"→ {len(findings)} after de-duplication")

    print("→ enriching with CISA KEV + FIRST EPSS")
    kev = load_kev(cache / "kev.json")
    epss = load_epss(cache / "epss.csv.gz")
    print(f"   KEV entries: {len(kev)} · EPSS entries: {len(epss)}")

    score(findings, policy, kev, epss)
    apply_baseline(findings, Path(args.baseline) if args.baseline else None)
    exceptions, expired = apply_exceptions(findings, Path(args.exceptions) if args.exceptions else None)
    llm_triage(findings, policy)

    k = kpis(findings)
    meta = {
        "repo": args.repo, "ref": args.ref, "sha": args.sha, "run_url": args.run_url,
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }
    passed, reasons = evaluate_gate(findings, policy, args.ref or "", expired)

    (out / "findings.json").write_text(json.dumps(
        {"meta": meta, "kpis": k, "gate": {"passed": passed, "reasons": reasons},
         "exceptions": exceptions,
         "findings": [asdict(f) for f in findings]}, indent=1, default=str), encoding="utf-8")
    (out / "baseline.json").write_text(json.dumps(
        {"generated": meta["generated"], "sha": args.sha,
         "fingerprints": sorted(f.fingerprint for f in findings)}, indent=1), encoding="utf-8")

    sbom = load_sbom(inp)
    expiring = [e for e in exceptions if isinstance(e.get("_days_left"), int) and 0 <= e["_days_left"] <= 30]

    if args.markdown:
        write_markdown(out / "summary.md", findings, k, meta, passed, reasons, expiring)
        print("→ wrote summary.md")
    if args.sarif:
        write_sarif(out / "consolidated.sarif", findings)
        print("→ wrote consolidated.sarif")
    if args.xlsx:
        write_xlsx(out / "devsecops-report.xlsx", findings, k, meta, sbom, exceptions, policy)
        print("→ wrote devsecops-report.xlsx")
    if args.pdf:
        write_pdf(out / "devsecops-report.pdf", findings, k, meta, exceptions, policy,
                  passed, reasons, out / "charts")
        print("→ wrote devsecops-report.pdf")

    print(f"\n{'PASS' if passed else 'FAIL'} — {k['total']} findings "
          f"({k['new']} new, {k['kev']} KEV, {k['verified_secrets']} verified secrets)")
    return 0   # `run` always succeeds; `gate` decides the build


def cmd_gate(args: argparse.Namespace) -> int:
    data = json.loads(Path(args.results).read_text())
    passed = data.get("gate", {}).get("passed", True)
    reasons = data.get("gate", {}).get("reasons", [])
    if passed:
        print("✅ Security gate PASSED")
        return 0
    print("❌ Security gate FAILED\n")
    for r in reasons:
        print(f"  • {r}")
    print("\nOptions:\n"
          "  1. Fix the finding (preferred, and usually a version bump).\n"
          "  2. Add a time-boxed, approved entry to security/exceptions.yaml.\n"
          "  3. If the rule is wrong, tune it in .config/ — and tell everyone why.\n"
          "Full PDF and Excel reports are attached to this workflow run.")
    return 1


def main() -> int:
    ap = argparse.ArgumentParser(prog="secreport", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="aggregate scanner output and build reports")
    r.add_argument("--input", required=True)
    r.add_argument("--out", default="reports")
    r.add_argument("--policy", default="security/risk-policy.yaml")
    r.add_argument("--exceptions", default="security/exceptions.yaml")
    r.add_argument("--baseline", default="")
    r.add_argument("--repo", default=os.getenv("GITHUB_REPOSITORY", "local"))
    r.add_argument("--ref", default=os.getenv("GITHUB_REF_NAME", "local"))
    r.add_argument("--sha", default=os.getenv("GITHUB_SHA", "0" * 40))
    r.add_argument("--run-url", dest="run_url", default="")
    r.add_argument("--pdf", action="store_true")
    r.add_argument("--xlsx", action="store_true")
    r.add_argument("--sarif", action="store_true")
    r.add_argument("--markdown", action="store_true")
    r.set_defaults(func=cmd_run)

    g = sub.add_parser("gate", help="exit non-zero if the risk policy is violated")
    g.add_argument("--results", default="reports/findings.json")
    g.add_argument("--policy", default="security/risk-policy.yaml")
    g.set_defaults(func=cmd_gate)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
