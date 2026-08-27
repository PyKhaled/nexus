# frozen_string_literal: true

require "minitest/autorun"
require "json"
require "stringio"
require "tmpdir"
require_relative "../cli"

class NexusAssemblerCliTest < Minitest::Test
  ROOT = File.expand_path("../../..", __dir__)

  def setup
    @repository = NexusAssembler::Repository.new(ROOT)
  end

  def test_plan_command
    output = StringIO.new
    status = run_cli(["plan", "--blueprint", development_blueprint], output: output)

    assert_equal 0, status
    parsed = JSON.parse(output.string)
    assert_equal "nexus", parsed.fetch("product")
    assert_equal "passed", parsed.fetch("policyStatus")
  end

  def test_assemble_command
    Dir.mktmpdir("nexus-assembler-cli") do |directory|
      output = StringIO.new
      errors = StringIO.new
      destination = File.join(directory, "package")
      status = run_cli(
        ["assemble", "--blueprint", development_blueprint, "--output", destination],
        output: output, error: errors
      )

      assert_equal 0, status, errors.string
      assert File.file?(File.join(destination, "blueprint.yaml"))
      assert_equal destination, JSON.parse(output.string).fetch("deploymentPackage")
    end
  end

  def test_repository_list_with_no_declarations
    output = StringIO.new
    status = run_cli(
      ["repository", "list", "--blueprint", development_blueprint],
      output: output
    )

    assert_equal 0, status
    assert_equal [], JSON.parse(output.string).fetch("repositories")
  end

  def test_assemble_rejects_a_missing_required_repository
    Dir.mktmpdir("nexus-assembler-cli") do |directory|
      blueprint = NexusAssembler::Data.load_yaml(development_blueprint)
      blueprint["repositories"] = [
        {
          "name" => "missing-service",
          "url" => "https://example.com/missing-service.git",
          "path" => "system/missing-service",
          "required" => true
        }
      ]
      blueprint_path = File.join(directory, "blueprint.yaml")
      File.write(blueprint_path, NexusAssembler::Data.yaml(blueprint))
      errors = StringIO.new

      status = run_cli(
        ["assemble", "--blueprint", blueprint_path, "--output", File.join(directory, "out")],
        error: errors
      )

      assert_equal 2, status
      assert_includes errors.string, "repository validation failed"
      refute File.exist?(File.join(directory, "out"))
    end
  end

  def test_assemble_refuses_to_replace_without_force
    Dir.mktmpdir("nexus-assembler-cli") do |directory|
      destination = File.join(directory, "out")
      run_cli(["assemble", "--blueprint", development_blueprint, "--output", destination])

      errors = StringIO.new
      status = run_cli(["assemble", "--blueprint", development_blueprint, "--output", destination], error: errors)

      assert_equal 2, status
      assert_includes errors.string, "not empty"
    end
  end

  def test_validate_command
    Dir.mktmpdir("nexus-assembler-cli") do |directory|
      destination = File.join(directory, "out")
      run_cli(["assemble", "--blueprint", development_blueprint, "--output", destination])

      output = StringIO.new
      status = run_cli(["validate", destination], output: output)

      assert_equal 0, status
      assert_equal "passed", JSON.parse(output.string).fetch("status")
    end
  end

  def test_missing_required_option_is_rejected
    errors = StringIO.new
    status = run_cli(["assemble", "--blueprint", development_blueprint], error: errors)

    assert_equal 2, status
    assert_includes errors.string, "--output is required"
  end

  def test_invalid_command_returns_error
    errors = StringIO.new
    status = run_cli(["unknown"], error: errors)

    assert_equal 2, status
    assert_includes errors.string, "unknown command"
  end

  def test_removed_command_aliases_are_rejected
    %w[compose generate].each do |command|
      errors = StringIO.new
      status = run_cli([command], error: errors)

      assert_equal 2, status
      assert_includes errors.string, "unknown command"
    end
  end

  def test_removed_selection_option_is_rejected
    errors = StringIO.new
    status = run_cli(["plan", "--selection", development_blueprint], error: errors)

    assert_equal 2, status
    assert_includes errors.string, "invalid option: --selection"
  end

  def test_help_without_command_returns_nonzero
    output = StringIO.new
    status = run_cli([], output: output)

    assert_equal 1, status
    assert_includes output.string, "Usage: nexus"
  end

  def test_secrets_command
    website_env = File.join(ROOT, "system/system-website/.env")
    website_db_env = File.join(ROOT, "system/system-website-db/.env")
    original_website = File.read(website_env)
    original_website_db = File.read(website_db_env)
    File.write(website_env, "MYSQL_PASSWORD=test-value\n")
    File.write(website_db_env, "MYSQL_ROOT_PASSWORD=test-root-value\n")

    Dir.mktmpdir("nexus-assembler-cli") do |directory|
      output = StringIO.new
      errors = StringIO.new
      destination = File.join(directory, "secrets.env")
      status = run_cli(
        ["secrets", "--blueprint", development_blueprint, "--output", destination],
        output: output, error: errors
      )

      assert_equal 0, status, errors.string
      assert_includes File.read(destination), "MYSQL_PASSWORD=test-value"
      parsed = JSON.parse(output.string)
      assert_equal destination, parsed.fetch("output")
      assert_includes errors.string, "missing required secrets"
    end
  ensure
    File.write(website_env, original_website)
    File.write(website_db_env, original_website_db)
  end

  private

  def development_blueprint
    File.join(ROOT, "composition/examples/nexus-development.yaml")
  end

  def run_cli(argv, output: StringIO.new, error: StringIO.new)
    NexusAssembler::CLI.new(argv, output: output, error: error, repository: @repository).run
  end
end
