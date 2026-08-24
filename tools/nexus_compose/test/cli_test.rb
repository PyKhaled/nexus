# frozen_string_literal: true

require "minitest/autorun"
require "stringio"
require "tmpdir"
require_relative "../cli"

class NexusComposeCliTest < Minitest::Test
  ROOT = File.expand_path("../../..", __dir__)

  def setup
    @repository = NexusCompose::Repository.new(ROOT)
  end

  def test_list_components
    output = StringIO.new
    status = NexusCompose::CLI.new(
      %w[list components],
      output: output,
      error: StringIO.new,
      repository: @repository
    ).run

    assert_equal 0, status
    parsed = JSON.parse(output.string)
    assert_equal ["nginx"], parsed.fetch("gateway")
    assert_equal ["keycloak"], parsed.fetch("authentication")
  end

  def test_generate_command
    Dir.mktmpdir("nexus-compose-cli") do |directory|
      output = StringIO.new
      errors = StringIO.new
      status = NexusCompose::CLI.new(
        [
          "generate",
          "--selection", File.join(ROOT, "composition/examples/nexus-development.yaml"),
          "--output", File.join(directory, "out")
        ],
        output: output,
        error: errors,
        repository: @repository
      ).run

      assert_equal 0, status, errors.string
      assert File.file?(File.join(directory, "out", "compose.yml"))
      assert_equal "passed", JSON.parse(output.string).fetch("status")
    end
  end

  def test_invalid_command_returns_error
    errors = StringIO.new
    status = NexusCompose::CLI.new(
      ["unknown"],
      output: StringIO.new,
      error: errors,
      repository: @repository
    ).run

    assert_equal 2, status
    assert_includes errors.string, "unknown command"
  end
end
