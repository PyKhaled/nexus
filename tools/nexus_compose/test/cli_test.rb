# frozen_string_literal: true

require "minitest/autorun"
require "json"
require "stringio"
require "tmpdir"
require_relative "../cli"

class NexusComposeCliTest < Minitest::Test
  ROOT = File.expand_path("../../..", __dir__)

  def setup
    @repository = NexusCompose::Repository.new(ROOT)
  end

  def test_plan_command
    output = StringIO.new
    status = run_cli(["plan", "--selection", development_selection], output: output)

    assert_equal 0, status
    parsed = JSON.parse(output.string)
    assert_equal "nexus", parsed.fetch("product")
    assert_equal "passed", parsed.fetch("policyStatus")
  end

  def test_generate_command
    Dir.mktmpdir("nexus-compose-cli") do |directory|
      output = StringIO.new
      errors = StringIO.new
      status = run_cli(
        ["generate", "--selection", development_selection, "--output", File.join(directory, "out")],
        output: output, error: errors
      )

      assert_equal 0, status, errors.string
      assert File.file?(File.join(directory, "out", "compose.yml"))
      assert_equal "passed", JSON.parse(output.string).fetch("status")
    end
  end

  def test_generate_refuses_to_replace_without_force
    Dir.mktmpdir("nexus-compose-cli") do |directory|
      destination = File.join(directory, "out")
      run_cli(["generate", "--selection", development_selection, "--output", destination])

      errors = StringIO.new
      status = run_cli(["generate", "--selection", development_selection, "--output", destination], error: errors)

      assert_equal 2, status
      assert_includes errors.string, "not empty"
    end
  end

  def test_validate_command
    Dir.mktmpdir("nexus-compose-cli") do |directory|
      destination = File.join(directory, "out")
      run_cli(["generate", "--selection", development_selection, "--output", destination])

      output = StringIO.new
      status = run_cli(["validate", destination], output: output)

      assert_equal 0, status
      assert_equal "passed", JSON.parse(output.string).fetch("status")
    end
  end

  def test_missing_required_option_is_rejected
    errors = StringIO.new
    status = run_cli(["generate", "--selection", development_selection], error: errors)

    assert_equal 2, status
    assert_includes errors.string, "--output is required"
  end

  def test_invalid_command_returns_error
    errors = StringIO.new
    status = run_cli(["unknown"], error: errors)

    assert_equal 2, status
    assert_includes errors.string, "unknown command"
  end

  def test_help_without_command_returns_nonzero
    output = StringIO.new
    status = run_cli([], output: output)

    assert_equal 1, status
    assert_includes output.string, "Usage: nexus-compose"
  end

  private

  def development_selection
    File.join(ROOT, "composition/examples/nexus-development.yaml")
  end

  def run_cli(argv, output: StringIO.new, error: StringIO.new)
    NexusCompose::CLI.new(argv, output: output, error: error, repository: @repository).run
  end
end
