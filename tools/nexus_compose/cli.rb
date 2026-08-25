# frozen_string_literal: true

require "json"
require "optparse"
require_relative "compiler"

module NexusCompose
  class CLI
    def initialize(argv, input: $stdin, output: $stdout, error: $stderr, repository: Repository.new)
      @argv = argv.dup
      @input = input
      @output = output
      @error = error
      @repository = repository
      @compiler = Compiler.new(repository)
    end

    def run
      command = @argv.shift
      case command
      when "plan" then plan
      when "generate" then generate
      when "validate" then validate
      when "version", "--version", "-v"
        @output.puts VERSION
        0
      when "help", "--help", "-h", nil
        @output.puts help
        command.nil? ? 1 : 0
      else
        raise ValidationError, "unknown command #{command.inspect}\n\n#{help}"
      end
    rescue NexusCompose::Error, OptionParser::ParseError => e
      @error.puts "error: #{e.message}"
      2
    end

    private

    def plan
      options = {}
      parser = OptionParser.new do |opts|
        opts.banner = "Usage: nexus-compose plan --selection FILE"
        opts.on("--selection FILE", "Composition selection YAML") { |value| options[:selection] = value }
      end
      parser.parse!(@argv)
      require_option!(options, :selection)

      @output.puts JSON.pretty_generate(Data.canonical(@compiler.plan(options.fetch(:selection))))
      0
    end

    def generate
      options = {force: false}
      parser = OptionParser.new do |opts|
        opts.banner = "Usage: nexus-compose generate --selection FILE --output DIRECTORY [--force]"
        opts.on("--selection FILE", "Composition selection YAML") { |value| options[:selection] = value }
        opts.on("--output DIRECTORY", "Generated deployment directory") { |value| options[:output] = value }
        opts.on("--force", "Replace existing generated files") { options[:force] = true }
      end
      parser.parse!(@argv)
      require_option!(options, :selection)
      require_option!(options, :output)

      result = @compiler.compile(options.fetch(:selection))
      destination = @compiler.write(result, options.fetch(:output), force: options.fetch(:force))
      @output.puts JSON.pretty_generate(
        "status" => result.policy_report.fetch("status"),
        "output" => destination,
        "services" => result.compose.fetch("services").keys.sort,
        "policyReport" => File.join(destination, "policy-report.json")
      )
      result.policy_report.fetch("status") == "passed" ? 0 : 3
    end

    def validate
      parser = OptionParser.new
      parser.banner = "Usage: nexus-compose validate COMPOSE_FILE_OR_DIRECTORY"
      parser.parse!(@argv)
      path = @argv.shift
      raise ValidationError, parser.banner unless path
      raise ValidationError, "unexpected arguments: #{@argv.join(' ')}" unless @argv.empty?

      report = @compiler.validate_generated(path)
      @output.puts JSON.pretty_generate(Data.canonical(report))
      0
    end

    def require_option!(options, key)
      raise ValidationError, "--#{key} is required" unless options[key]
    end

    def help
      <<~HELP
        Nexus Composition Generator #{VERSION}

        Usage: nexus-compose COMMAND [OPTIONS]

        Commands:
          plan       Resolve a selection without writing generated files
          generate   Create Compose and its deployment evidence package
          validate   Validate a generated Compose file or directory
          version    Print the generator version
          help       Show this help
      HELP
    end
  end
end
