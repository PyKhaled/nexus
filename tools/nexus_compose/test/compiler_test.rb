# frozen_string_literal: true

require "minitest/autorun"
require "tmpdir"
require_relative "../compiler"

class NexusComposeCompilerTest < Minitest::Test
  ROOT = File.expand_path("../../..", __dir__)

  def setup
    @repository = NexusCompose::Repository.new(ROOT)
    @compiler = NexusCompose::Compiler.new(@repository)
  end

  def test_development_example_resolves_complete_foundation
    result = @compiler.compile(example("nexus-development.yaml"))

    assert_equal "nexus", result.compose.fetch("name")
    assert_equal "nexus-system", result.compose.dig("networks", "system", "name")
    assert_equal %w[gateway keycloak keycloak-db status status-redis website website-db],
                 result.compose.fetch("services").keys.sort
    assert result.compose.dig("services", "gateway").key?("build")
    assert result.lock.fetch("artifacts").none? { |artifact| artifact.fetch("digestResolved") }
    result.compose.fetch("services").each_value do |service|
      next unless service.dig("healthcheck", "test")

      assert service.dig("healthcheck", "test").all? { |item| item.is_a?(String) }
    end
    assert_equal "passed", result.policy_report.fetch("status")
  end

  def test_development_example_matches_reviewed_root_compose
    result = @compiler.compile(example("nexus-development.yaml"))
    reviewed = NexusCompose::Data.load_yaml(File.join(ROOT, "compose.yml"))

    assert_equal NexusCompose::Data.canonical(reviewed), NexusCompose::Data.canonical(result.compose)
  end

  def test_dependency_resolution_adds_gateway
    selection = selection_hash(
      edition: "custom",
      capabilities: {"gateway" => "nginx", "authentication" => "keycloak"}
    )

    result = @compiler.compile(selection)

    assert_equal %w[authentication gateway], result.components.map { |component| component.fetch("capability") }
  end

  def test_optional_capability_choices_change_generated_services
    selection = selection_hash(
      edition: "community",
      capabilities: {
        "website" => "disabled",
        "service-status" => "kener"
      }
    )

    result = @compiler.compile(selection)

    assert_equal %w[gateway keycloak keycloak-db status status-redis], result.compose.fetch("services").keys.sort
    warning_ids = result.policy_report.fetch("warnings").map { |warning| warning.fetch("id") }
    assert_includes warning_ids, "dormant-gateway-route-website"
  end

  def test_required_capability_cannot_be_disabled
    selection = selection_hash(
      edition: "community",
      capabilities: {"gateway" => "disabled"}
    )

    error = assert_raises(NexusCompose::ValidationError) { @compiler.compile(selection) }
    assert_includes error.message, "edition requires capabilities"
  end

  def test_hardened_production_uses_private_digest_images_without_runtime_builds
    result = @compiler.compile(example("nexus-self-hosted-production.yaml"))
    services = result.compose.fetch("services")

    services.each_value do |service|
      refute service.key?("build")
      assert_match %r{\Aregistry\.example\.com/nexus/}, service.fetch("image")
      assert_includes service.fetch("image"), "@${"
      assert_equal false, service.fetch("privileged")
      assert_includes service.fetch("security_opt"), "no-new-privileges:true"
    end
    refute_includes NexusCompose::Data.yaml(result.compose), "change-me"
    assert_equal "1", services.dig("gateway", "environment", "GATEWAY_TLS_REDIRECT")
    assert_includes services.dig("gateway", "ports"), "${GATEWAY_HTTPS_PORT:-443}:443"
    assert services.dig("gateway", "volumes").any? { |mount| mount.include?("/etc/nginx/ssl:ro") }
    assert_equal "https://${STATUS_DOMAIN:?STATUS_DOMAIN is required}", services.dig("status", "environment", "ORIGIN")
    assert_equal "passed", result.policy_report.fetch("status")
    assert result.build_plan.dig("requirements", "sbom")
    assert result.build_plan.dig("requirements", "signature")
  end

  def test_high_assurance_is_private_only_and_denies_default_network_egress
    result = @compiler.compile(example("nexus-high-assurance.yaml"))

    assert_equal true, result.compose.dig("networks", "system", "internal")
    assert_equal "passed", result.policy_report.fetch("status")
    assert result.policy_report.fetch("warnings").any? { |warning| warning["id"] == "host-controls-outside-compose" }
  end

  def test_high_assurance_rejects_non_private_registry_policy
    selection = NexusCompose::Data.load_yaml(example("nexus-high-assurance.yaml"))
    selection.fetch("registry")["policy"] = "private-preferred"

    error = assert_raises(NexusCompose::ValidationError) { @compiler.compile(selection) }
    assert_includes error.message, "private-only"
  end

  def test_generation_is_deterministic_and_writes_complete_package
    first = @compiler.compile(example("nexus-development.yaml"))
    second = @compiler.compile(example("nexus-development.yaml"))

    assert_equal NexusCompose::Data.yaml(first.compose), NexusCompose::Data.yaml(second.compose)
    assert_equal NexusCompose::Data.yaml(first.lock), NexusCompose::Data.yaml(second.lock)

    Dir.mktmpdir("nexus-compose-test") do |directory|
      destination = File.join(directory, "generated")
      @compiler.write(first, destination)
      expected = %w[.env.example README.md build-plan.yaml compose.lock.yaml compose.yml policy-report.json runtime secrets.required selection.yaml]
      assert_equal expected, Dir.children(destination).sort
      written = NexusCompose::Data.load_yaml(File.join(destination, "compose.yml"))
      assert_equal first.compose.fetch("name"), written.fetch("name")
      assert_equal first.compose.fetch("services").keys.sort, written.fetch("services").keys.sort
      gateway_context = written.dig("services", "gateway", "build", "context")
      assert_equal File.join(ROOT, "system/system-gateway"), File.expand_path(gateway_context, destination)
    end
  end

  def test_write_refuses_to_replace_existing_output_without_force
    result = @compiler.compile(example("nexus-development.yaml"))
    Dir.mktmpdir("nexus-compose-test") do |directory|
      File.write(File.join(directory, "owned.txt"), "preserve")
      assert_raises(NexusCompose::Error) { @compiler.write(result, directory) }
      assert_equal "preserve", File.read(File.join(directory, "owned.txt"))
    end
  end

  def test_production_package_contains_portable_auth_assets
    result = @compiler.compile(example("nexus-self-hosted-production.yaml"))
    Dir.mktmpdir("nexus-compose-production") do |directory|
      destination = File.join(directory, "generated")
      @compiler.write(result, destination)
      compose = NexusCompose::Data.load_yaml(File.join(destination, "compose.yml"))

      assert_includes compose.dig("services", "keycloak-db", "volumes"), "keycloak-db-data:/var/lib/postgresql/data"
      assert File.file?(File.join(destination, "assets/auth/realm-config/nexus-realm.json"))
      assert File.file?(File.join(destination, "assets/auth/postgres/postgresql.conf"))
      assert File.file?(File.join(destination, "assets/gateway/templates-tls/01-default-tls.conf.template"))
      assert File.file?(File.join(destination, "runtime/auth.env.example"))
      refute_includes File.read(File.join(destination, ".env.example")), "KC_DB_PASSWORD="
      assert_equal "passed", @compiler.validate_generated(destination).fetch("package").fetch("status")
    end
  end

  def test_unknown_implementation_is_rejected
    selection = selection_hash(
      edition: "custom",
      capabilities: {"gateway" => "not-real"}
    )

    error = assert_raises(NexusCompose::ValidationError) { @compiler.compile(selection) }
    assert_includes error.message, "unknown implementation"
  end

  def test_unknown_selection_fields_are_rejected
    selection = selection_hash(edition: "custom", capabilities: {"gateway" => "nginx"})
    selection["profile"] = "production"

    error = assert_raises(NexusCompose::ValidationError) { @compiler.compile(selection) }
    assert_includes error.message, "unknown selection fields"
  end

  private

  def example(name)
    File.join(ROOT, "composition", "examples", name)
  end

  def selection_hash(edition:, capabilities:)
    {
      "apiVersion" => "nexus.io/composition/v1alpha1",
      "product" => {"name" => "test-product", "edition" => edition},
      "deployment" => {
        "target" => "local",
        "environment" => "development",
        "assurance" => "standard"
      },
      "capabilities" => capabilities
    }
  end
end
