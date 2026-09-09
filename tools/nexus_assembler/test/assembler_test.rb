# frozen_string_literal: true

require "minitest/autorun"
require "minitest/mock"
require "tmpdir"
require_relative "../assembler"
require_relative "support/secret_repository_fixture"

class NexusAssemblerTest < Minitest::Test
  include SecretRepositoryFixture
  ROOT = File.expand_path("../../..", __dir__)

  def setup
    @repository = NexusAssembler::Repository.new(ROOT)
    @assembler = NexusAssembler::Assembler.new(@repository)
  end

  def test_assembler_exposes_canonical_vocabulary
    result = @assembler.assemble(example("nexus-development.yaml"))

    assert result.lock.key?("blueprintDigest")
    assert_equal "nexus-assembler", result.lock.dig("assembler", "name")
  end

  def test_development_example_resolves_complete_foundation
    result = @assembler.assemble(example("nexus-development.yaml"))

    assert_equal "nexus-development", result.compose.fetch("name")
    assert_equal "nexus-system", result.compose.dig("networks", "system", "name")
    assert_equal %w[gateway keycloak keycloak-db overseer status status-redis website website-db],
                 result.compose.fetch("services").keys.sort
    assert result.compose.dig("services", "gateway").key?("build")
    assert_equal "${APP_DOMAIN:-localhost}", result.compose.dig("services", "gateway", "environment", "APP_DOMAIN")
    assert_includes result.compose.dig("services", "gateway", "networks", "system", "aliases"),
                    "${APP_DOMAIN:-localhost}"
    assert result.lock.fetch("artifacts").none? { |artifact| artifact.fetch("digestResolved") }
    result.compose.fetch("services").each_value do |service|
      next unless service.dig("healthcheck", "test")

      assert service.dig("healthcheck", "test").all? { |item| item.is_a?(String) }
    end
    assert_equal "passed", result.policy_report.fetch("status")
  end

  def test_primary_website_route_preserves_gateway_health_endpoints
    default_route = File.join(ROOT, "system/system-gateway/conf.d/default.conf")
    http_route = File.read(File.join(ROOT, "system/system-gateway/templates/10-app.conf.template"))
    tls_route = File.read(File.join(ROOT, "system/system-gateway/templates-tls/11-app-tls.conf.template"))

    assert File.file?(default_route), "Nexus must replace the base NGINX image's localhost default vhost"
    [http_route, tls_route].each do |route|
      assert_includes route, "server_name ${APP_DOMAIN};"
      assert_includes route, "location = /healthz {"
      assert_includes route, "location = /readyz {"
      assert_includes route, "location / {"
      assert_includes route, "proxy_pass http://$gateway_app_upstream;"
    end
  end

  def test_development_example_matches_reviewed_root_compose
    result = @assembler.assemble(example("nexus-development.yaml"))
    reviewed = NexusAssembler::Data.load_yaml(File.join(ROOT, "compose.yml"))

    assert_equal NexusAssembler::Data.canonical(reviewed), NexusAssembler::Data.canonical(result.compose)
  end

  def test_dependency_resolution_adds_gateway
    blueprint = blueprint_hash(
      edition: "custom",
      capabilities: {"gateway" => "nginx", "authentication" => "keycloak"}
    )

    result = @assembler.assemble(blueprint)

    assert_equal %w[authentication gateway], result.components.map { |component| component.fetch("capability") }
  end

  def test_duplicate_compose_service_ownership_is_rejected
    left = {"services" => {"shared" => {"image" => "example/one"}}}
    right = {"services" => {"shared" => {"image" => "example/two"}}}

    error = assert_raises(NexusAssembler::ValidationError) do
      NexusAssembler::Data.deep_merge(left, right)
    end

    assert_includes error.message, "duplicate Compose service"
  end

  def test_optional_capability_choices_change_generated_services
    blueprint = blueprint_hash(
      edition: "community",
      capabilities: {
        "website" => "disabled",
        "service-status" => "kener",
        "observability" => "overseer"
      }
    )

    result = @assembler.assemble(blueprint)

    assert_equal %w[gateway keycloak keycloak-db overseer status status-redis], result.compose.fetch("services").keys.sort
    warning_ids = result.policy_report.fetch("warnings").map { |warning| warning.fetch("id") }
    assert_includes warning_ids, "dormant-gateway-route-website"
  end

  def test_required_capability_cannot_be_disabled
    blueprint = blueprint_hash(
      edition: "community",
      capabilities: {"gateway" => "disabled"}
    )

    error = assert_raises(NexusAssembler::ValidationError) { @assembler.assemble(blueprint) }
    assert_includes error.message, "edition requires capabilities"
  end

  def test_hardened_production_uses_private_digest_images_without_runtime_builds
    result = @assembler.assemble(example("nexus-self-hosted-production.yaml"))
    services = result.compose.fetch("services")

    services.each_value do |service|
      refute service.key?("build")
      assert_match %r{\Aregistry\.example\.com/nexus/}, service.fetch("image")
      assert_includes service.fetch("image"), "@${"
      assert_equal false, service.fetch("privileged")
      assert_includes service.fetch("security_opt"), "no-new-privileges:true"
    end
    refute_includes NexusAssembler::Data.yaml(result.compose), "change-me"
    assert_equal "1", services.dig("gateway", "environment", "GATEWAY_TLS_REDIRECT")
    assert_includes services.dig("gateway", "ports"), "${GATEWAY_HTTPS_PORT:-443}:443"
    assert services.dig("gateway", "volumes").any? { |mount| mount.include?("/etc/nginx/ssl:ro") }
    assert_equal "passed", result.policy_report.fetch("status")
    assert result.build_plan.dig("requirements", "sbom")
    assert result.build_plan.dig("requirements", "signature")
  end

  def test_high_assurance_is_private_only_and_denies_default_network_egress
    result = @assembler.assemble(example("nexus-high-assurance.yaml"))

    assert_equal true, result.compose.dig("networks", "system", "internal")
    assert_equal "passed", result.policy_report.fetch("status")
    assert result.policy_report.fetch("warnings").any? { |warning| warning["id"] == "host-controls-outside-compose" }
  end

  def test_high_assurance_rejects_non_private_registry_policy
    blueprint = NexusAssembler::Data.load_yaml(example("nexus-high-assurance.yaml"))
    blueprint.fetch("registry")["policy"] = "private-preferred"

    error = assert_raises(NexusAssembler::ValidationError) { @assembler.assemble(blueprint) }
    assert_includes error.message, "private-only"
  end

  def test_generation_is_deterministic_and_writes_complete_package
    first = @assembler.assemble(example("nexus-development.yaml"))
    second = @assembler.assemble(example("nexus-development.yaml"))

    assert_equal NexusAssembler::Data.yaml(first.compose), NexusAssembler::Data.yaml(second.compose)
    assert_equal NexusAssembler::Data.yaml(first.lock), NexusAssembler::Data.yaml(second.lock)

    Dir.mktmpdir("nexus-assembler-test") do |directory|
      destination = File.join(directory, "generated")
      @assembler.write_deployment_package(first, destination)
      expected = %w[.env.example README.md blueprint.yaml build-plan.yaml compose.lock.yaml compose.yml policy-report.json runtime secrets.required]
      assert_equal expected, Dir.children(destination).sort
      written = NexusAssembler::Data.load_yaml(File.join(destination, "compose.yml"))
      assert_equal first.compose.fetch("name"), written.fetch("name")
      assert_equal first.compose.fetch("services").keys.sort, written.fetch("services").keys.sort
      gateway_context = written.dig("services", "gateway", "build", "context")
      assert_equal File.join(ROOT, "system/system-gateway"), File.expand_path(gateway_context, destination)
    end
  end

  def test_write_refuses_to_replace_existing_output_without_force
    result = @assembler.assemble(example("nexus-development.yaml"))
    Dir.mktmpdir("nexus-assembler-test") do |directory|
      File.write(File.join(directory, "owned.txt"), "preserve")
      assert_raises(NexusAssembler::Error) { @assembler.write_deployment_package(result, directory) }
      assert_equal "preserve", File.read(File.join(directory, "owned.txt"))
    end
  end

  def test_force_replaces_generated_package_without_stale_files
    production = @assembler.assemble(example("nexus-self-hosted-production.yaml"))
    gateway_only = @assembler.assemble(
      blueprint_hash(edition: "custom", capabilities: {"gateway" => "nginx"})
    )

    Dir.mktmpdir("nexus-assembler-force") do |directory|
      destination = File.join(directory, "generated")
      @assembler.write_deployment_package(production, destination)
      File.write(File.join(destination, "stale.txt"), "remove me")

      @assembler.write_deployment_package(gateway_only, destination, force: true)

      refute File.exist?(File.join(destination, "stale.txt"))
      refute File.exist?(File.join(destination, "assets"))
      refute File.exist?(File.join(destination, "runtime"))
      assert_equal gateway_only.compose.fetch("services").keys.sort,
                   NexusAssembler::Data.load_yaml(File.join(destination, "compose.yml")).fetch("services").keys.sort
    end
  end

  def test_production_package_contains_portable_auth_assets
    result = @assembler.assemble(example("nexus-self-hosted-production.yaml"))
    Dir.mktmpdir("nexus-assembler-production") do |directory|
      destination = File.join(directory, "generated")
      @assembler.write_deployment_package(result, destination)
      compose = NexusAssembler::Data.load_yaml(File.join(destination, "compose.yml"))

      assert_includes compose.dig("services", "keycloak-db", "volumes"), "keycloak-db-data:/var/lib/postgresql/data"
      assert File.file?(File.join(destination, "assets/auth/realm-config/nexus-realm.json"))
      assert File.file?(File.join(destination, "assets/auth/postgres/postgresql.conf"))
      assert File.file?(File.join(destination, "assets/gateway/templates-tls/01-default-tls.conf.template"))
      assert File.file?(File.join(destination, "runtime/auth.env.example"))
      refute_includes File.read(File.join(destination, ".env.example")), "KC_DB_PASSWORD="
      assert_equal "passed", @assembler.validate_deployment_package(destination).fetch("package").fetch("status")
    end
  end

  def test_unknown_implementation_is_rejected
    blueprint = blueprint_hash(
      edition: "custom",
      capabilities: {"gateway" => "not-real"}
    )

    error = assert_raises(NexusAssembler::ValidationError) { @assembler.assemble(blueprint) }
    assert_includes error.message, "unknown implementation"
  end

  def test_unknown_blueprint_fields_are_rejected
    blueprint = blueprint_hash(edition: "custom", capabilities: {"gateway" => "nginx"})
    blueprint["profile"] = "production"

    error = assert_raises(NexusAssembler::ValidationError) { @assembler.assemble(blueprint) }
    assert_includes error.message, "unknown blueprint fields"
  end

  def test_repository_declarations_are_accepted
    blueprint = blueprint_hash(edition: "custom", capabilities: {"gateway" => "nginx"})
    blueprint["repositories"] = [
      {
        "name" => "system-service",
        "url" => "git@github.com:example/system-service.git",
        "path" => "system/system-service",
        "branch" => "main",
        "required" => true
      }
    ]

    result = @assembler.assemble(blueprint)

    assert_equal "system/system-service", result.blueprint.fetch("repositories").first.fetch("path")
    plan = @assembler.plan(blueprint)
    assert_equal "system-service", plan.fetch("repositories").first.fetch("name")
  end

  def test_repository_paths_must_be_below_system
    blueprint = blueprint_hash(edition: "custom", capabilities: {"gateway" => "nginx"})
    blueprint["repositories"] = [
      {"name" => "escape", "url" => "https://example.com/escape.git", "path" => "../escape"}
    ]

    error = assert_raises(NexusAssembler::ValidationError) { @assembler.assemble(blueprint) }

    assert_includes error.message, "below system/"
  end

  def test_duplicate_repository_paths_are_rejected
    blueprint = blueprint_hash(edition: "custom", capabilities: {"gateway" => "nginx"})
    blueprint["repositories"] = [
      {"name" => "one", "url" => "https://example.com/one.git", "path" => "system/shared"},
      {"name" => "two", "url" => "https://example.com/two.git", "path" => "system/shared"}
    ]

    error = assert_raises(NexusAssembler::ValidationError) { @assembler.assemble(blueprint) }

    assert_includes error.message, "duplicate repository paths"
  end

  def test_collect_secrets_merges_selected_components_env_files
    with_secret_repository(website: "MYSQL_PASSWORD=test-value\n", database: "MYSQL_ROOT_PASSWORD=test-root-value\n") do |repository|
      Dir.mktmpdir("nexus-assembler-secrets") do |directory|
        output = File.join(directory, "secrets.env")
        report = NexusAssembler::Assembler.new(repository).collect_secrets(
          blueprint_hash(edition: "custom", capabilities: {"gateway" => "nginx", "website" => "wordpress"}),
          output
        )

        assert_equal %w[system/system-website-db/.env system/system-website/.env], report.fetch("envFiles").sort
        content = File.read(output)
        assert_includes content, "MYSQL_PASSWORD=test-value"
        assert_includes content, "MYSQL_ROOT_PASSWORD=test-root-value"
        assert_equal 0o600, File.stat(output).mode & 0o777
      end
    end
  end

  def test_collect_secrets_rejects_duplicate_keys
    with_secret_repository(website: "MYSQL_PASSWORD=one\n", database: "MYSQL_PASSWORD=two\n") do |repository|
      Dir.mktmpdir("nexus-assembler-secrets") do |directory|
        error = assert_raises(NexusAssembler::ValidationError) do
          NexusAssembler::Assembler.new(repository).collect_secrets(
            blueprint_hash(edition: "custom", capabilities: {"gateway" => "nginx", "website" => "wordpress"}),
            File.join(directory, "secrets.env")
          )
        end
        assert_includes error.message, "duplicate secret keys"
      end
    end
  end

  def test_collect_secrets_reports_missing_required_secrets
    with_secret_repository(website: "MYSQL_PASSWORD=synthetic-value\n") do |repository|
      report = NexusAssembler::Assembler.new(repository).collect_secrets(
        example("nexus-development.yaml"), File.join(repository.root, "secrets.env")
      )
      assert_includes report.fetch("missingRequired"), "KENER_SECRET_KEY"
    end
  end

  def test_collect_secrets_rejects_missing_env_files
    with_secret_repository do |repository|
      output = File.join(repository.root, "secrets.env")
      error = assert_raises(NexusAssembler::ValidationError) do
        NexusAssembler::Assembler.new(repository).collect_secrets(example("nexus-development.yaml"), output)
      end
      assert_includes error.message, "no .env files found"
      refute File.exist?(output)
    end
  end

  def test_secret_fixture_preserves_source_files_and_cleans_up_on_failure
    Dir.mktmpdir("nexus-secret-source") do |source|
      composition = File.join(source, "composition")
      FileUtils.mkdir_p(composition)
      sentinel = File.join(composition, ".env")
      File.write(sentinel, "SENTINEL=synthetic-preserve\n")
      File.chmod(0o600, sentinel)
      definition = File.join(composition, "fixture.yaml")
      File.write(definition, "synthetic: true\n")

      [:setup, :execution].each do |failure_stage|
        fixture_root = nil
        original_write = File.method(:write)
        writer = lambda do |path, content|
          fixture_root = File.expand_path("../..", File.dirname(path))
          if failure_stage == :setup && path.include?("system-website-db")
            raise IOError, "synthetic setup failure"
          end
          original_write.call(path, content)
        end

        assert_raises(IOError) do
          File.stub(:write, writer) do
            with_secret_repository(website: "FIRST=synthetic\n", database: "SECOND=synthetic\n",
                                   composition_root: composition) do |repository|
              assert_equal fixture_root, repository.root
              refute File.exist?(File.join(repository.root, "composition/.env"))
              assert_equal "synthetic: true\n", File.read(File.join(repository.root, "composition/fixture.yaml"))
              raise IOError, "synthetic execution failure"
            end
          end
        end
        refute_nil fixture_root
        refute File.exist?(fixture_root)
        assert_equal "SENTINEL=synthetic-preserve\n", File.read(sentinel)
        assert_equal 0o600, File.stat(sentinel).mode & 0o777
        assert_equal "synthetic: true\n", File.read(definition)
      end
    end
  end

  private

  def example(name)
    File.join(ROOT, "composition", "examples", name)
  end

  def blueprint_hash(edition:, capabilities:)
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
