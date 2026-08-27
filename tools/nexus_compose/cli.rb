# frozen_string_literal: true

require "json"
require "optparse"
require_relative "compiler"
require_relative "repository_manager"

module NexusCompose
  class CLI
    def initialize(argv, input: $stdin, output: $stdout, error: $stderr, repository: Repository.new,
                   repository_manager: nil, program_name: "nexus-compose")
      @argv = argv.dup
      @input = input
      @output = output
      @error = error
      @repository = repository
      @program_name = program_name
      @compiler = Compiler.new(repository)
      @repository_manager = repository_manager || RepositoryManager.new(repository)
    end

    def run
      command = @argv.shift
      case command
      when "plan" then plan
      when "generate", "compose" then generate(command)
      when "validate" then validate
      when "secrets" then secrets
      when "repository", "repo" then repository_command
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
        opts.banner = "Usage: #{@program_name} plan --selection FILE"
        opts.on("--selection FILE", "Composition selection YAML") { |value| options[:selection] = value }
      end
      parser.parse!(@argv)
      require_option!(options, :selection)

      @output.puts JSON.pretty_generate(Data.canonical(@compiler.plan(options.fetch(:selection))))
      0
    end

    def generate(command = "generate")
      options = {force: false}
      parser = OptionParser.new do |opts|
        opts.banner = "Usage: #{@program_name} #{command} --selection FILE --output DIRECTORY [--force]"
        opts.on("--selection FILE", "Composition selection YAML") { |value| options[:selection] = value }
        opts.on("--output DIRECTORY", "Generated deployment directory") { |value| options[:output] = value }
        opts.on("--force", "Replace existing generated files") { options[:force] = true }
      end
      parser.parse!(@argv)
      require_option!(options, :selection)
      require_option!(options, :output)

      @repository_manager.validate(options.fetch(:selection))
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

    def repository_command
      subcommand = @argv.shift
      case subcommand
      when "add" then repository_add
      when "list" then repository_list
      when "status" then repository_status
      when "sync" then repository_sync
      when "validate" then repository_validate
      when "help", "--help", "-h", nil
        @output.puts repository_help
        subcommand.nil? ? 1 : 0
      else
        raise ValidationError, "unknown repository command #{subcommand.inspect}\n\n#{repository_help}"
      end
    end

    def repository_add
      options = {required: true}
      parser = OptionParser.new do |opts|
        opts.banner = "Usage: #{@program_name} repository add NAME URL --selection FILE [--path PATH] [--branch BRANCH] [--optional]"
        opts.on("--selection FILE", "Composition selection YAML") { |value| options[:selection] = value }
        opts.on("--path PATH", "Checkout path below system/") { |value| options[:path] = value }
        opts.on("--branch BRANCH", "Branch used when adding the submodule") { |value| options[:branch] = value }
        opts.on("--optional", "Do not fail validation when this repository is absent") { options[:required] = false }
      end
      parser.parse!(@argv)
      require_option!(options, :selection)
      name = @argv.shift
      url = @argv.shift
      raise ValidationError, parser.banner unless name && url
      raise ValidationError, "unexpected arguments: #{@argv.join(' ')}" unless @argv.empty?

      report = @repository_manager.add(
        options.fetch(:selection),
        name: name,
        url: url,
        path: options[:path],
        branch: options[:branch],
        required: options.fetch(:required)
      )
      @output.puts JSON.pretty_generate(Data.canonical(report))
      0
    end

    def repository_list
      selection, = repository_selection_option("list")
      @output.puts JSON.pretty_generate("repositories" => Data.canonical(@repository_manager.list(selection)))
      0
    end

    def repository_status
      selection, = repository_selection_option("status")
      report = @repository_manager.status(selection)
      @output.puts JSON.pretty_generate(Data.canonical(report))
      report.fetch("status").start_with?("passed") ? 0 : 3
    end

    def repository_sync
      selection, = repository_selection_option("sync")
      report = @repository_manager.sync(selection)
      @output.puts JSON.pretty_generate(Data.canonical(report))
      0
    end

    def repository_validate
      selection, = repository_selection_option("validate")
      report = @repository_manager.validate(selection)
      @output.puts JSON.pretty_generate(Data.canonical(report))
      0
    end

    def repository_selection_option(command)
      options = {}
      parser = OptionParser.new do |opts|
        opts.banner = "Usage: #{@program_name} repository #{command} --selection FILE"
        opts.on("--selection FILE", "Composition selection YAML") { |value| options[:selection] = value }
      end
      parser.parse!(@argv)
      require_option!(options, :selection)
      raise ValidationError, "unexpected arguments: #{@argv.join(' ')}" unless @argv.empty?

      [options.fetch(:selection), parser]
    end

    def validate
      parser = OptionParser.new
      parser.banner = "Usage: #{@program_name} validate COMPOSE_FILE_OR_DIRECTORY"
      parser.parse!(@argv)
      path = @argv.shift
      raise ValidationError, parser.banner unless path
      raise ValidationError, "unexpected arguments: #{@argv.join(' ')}" unless @argv.empty?

      report = @compiler.validate_generated(path)
      @output.puts JSON.pretty_generate(Data.canonical(report))
      0
    end

    def secrets
      options = {}
      parser = OptionParser.new do |opts|
        opts.banner = "Usage: #{@program_name} secrets --selection FILE --output FILE"
        opts.on("--selection FILE", "Composition selection YAML") { |value| options[:selection] = value }
        opts.on("--output FILE", "Merged secrets env file") { |value| options[:output] = value }
      end
      parser.parse!(@argv)
      require_option!(options, :selection)
      require_option!(options, :output)

      report = @compiler.collect_secrets(options.fetch(:selection), options.fetch(:output))
      @output.puts JSON.pretty_generate(Data.canonical(report))
      if report.fetch("missingRequired").any?
        @error.puts "warning: missing required secrets: #{report.fetch('missingRequired').join(', ')}"
      end
      0
    end

    def require_option!(options, key)
      raise ValidationError, "--#{key} is required" unless options[key]
    end

    def help
      <<~HELP
        Nexus Composition Generator #{VERSION}

        Usage: #{@program_name} COMMAND [OPTIONS]

        Commands:
          plan       Resolve a selection without writing generated files
          compose    Create Compose and its deployment evidence package
          generate   Create Compose and its deployment evidence package
          validate   Validate a generated Compose file or directory
          secrets    Merge selected components' .env files into one secrets file
          repository Manage source repositories under system/
          version    Print the generator version
          help       Show this help
      HELP
    end

    def repository_help
      <<~HELP
        Usage: #{@program_name} repository COMMAND [OPTIONS]

        Commands:
          add        Add and clone a repository as a Git submodule
          list       List declared repositories and their local state
          status     Report whether repositories are initialized
          sync       Create missing submodules, then sync and initialize them
          validate   Validate declarations, .gitmodules, and working trees locally
          help       Show this help
      HELP
    end
  end
end
