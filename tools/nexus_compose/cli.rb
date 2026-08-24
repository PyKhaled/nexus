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
      when "generate" then generate
      when "plan" then plan
      when "validate" then validate
      when "configure" then configure
      when "list" then list
      when "explain" then explain
      when "diff" then diff
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

    def validate
      parser = OptionParser.new
      parser.banner = "Usage: nexus-compose validate COMPOSE_FILE_OR_DIRECTORY"
      parser.parse!(@argv)
      path = @argv.shift
      raise ValidationError, parser.banner unless path
      raise ValidationError, "unexpected arguments: #{@argv.join(' ')}" unless @argv.empty?

      @output.puts JSON.pretty_generate(Data.canonical(@compiler.validate_generated(path)))
      0
    end

    def configure
      options = {output: "composition/selection.yaml", force: false}
      parser = OptionParser.new do |opts|
        opts.banner = "Usage: nexus-compose configure [--output FILE] [--force]"
        opts.on("--output FILE", "Write selection YAML") { |value| options[:output] = value }
        opts.on("--force", "Replace an existing selection") { options[:force] = true }
      end
      parser.parse!(@argv)
      destination = File.expand_path(options.fetch(:output))
      if File.exist?(destination) && !options.fetch(:force)
        raise Error, "selection already exists: #{destination}; pass --force to replace it"
      end

      product_name = prompt("Product name", "nexus")
      edition_id = choose("Edition", @repository.dimensions("editions"), "enterprise")
      target_id = choose("Deployment target", @repository.dimensions("targets"), "local")
      environment_candidates = @repository.load_dimension("targets", target_id).fetch("allowedEnvironments")
      environment_id = choose("Environment", environment_candidates, environment_candidates.first)
      assurance_candidates = @repository.dimensions("assurance")
      assurance_candidates -= ["high-assurance"] unless target_id == "self-hosted" && environment_id == "production"
      assurance_id = choose("Assurance profile", assurance_candidates, "standard")

      edition = @repository.load_dimension("editions", edition_id)
      choices = {}
      Array(edition["allowed"]).sort.each do |capability|
        implementations = @repository.catalog.fetch(capability, {}).keys.sort
        next if implementations.empty?

        default = edition.fetch("defaults", {})[capability]
        required = Array(edition["required"]).include?(capability)
        enabled = required || yes_no?("Enable #{capability}?", !default.nil?)
        choices[capability] = enabled ? choose("#{capability} implementation", implementations, default || implementations.first) : "disabled"
      end

      registry_required = environment_id == "production" || %w[hardened high-assurance].include?(assurance_id)
      registry = nil
      if registry_required || yes_no?("Configure a private container registry?", false)
        registry = {
          "host" => prompt("Registry host", "registry.example.com"),
          "namespace" => prompt("Registry namespace", product_name),
          "policy" => assurance_id == "high-assurance" ? "private-only" : choose(
            "Registry policy",
            %w[public-allowed private-preferred private-only],
            "private-preferred"
          )
        }
      end

      selection = {
        "apiVersion" => "nexus.io/composition/v1alpha1",
        "product" => {"name" => product_name, "edition" => edition_id},
        "deployment" => {
          "target" => target_id,
          "environment" => environment_id,
          "assurance" => assurance_id
        },
        "capabilities" => choices
      }
      selection["registry"] = registry if registry
      @compiler.compile(selection)
      FileUtils.mkdir_p(File.dirname(destination))
      File.write(destination, Data.yaml(selection))
      @output.puts "Wrote #{destination}"
      0
    end

    def list
      parser = OptionParser.new
      parser.banner = "Usage: nexus-compose list [dimensions|components]"
      parser.parse!(@argv)
      subject = @argv.shift || "dimensions"
      data = case subject
             when "dimensions"
               {
                 "editions" => @repository.dimensions("editions"),
                 "environments" => @repository.dimensions("environments"),
                 "targets" => @repository.dimensions("targets"),
                 "assurance" => @repository.dimensions("assurance")
               }
             when "components"
               @repository.catalog.keys.sort.each_with_object({}) do |capability, result|
                 result[capability] = @repository.catalog.fetch(capability).keys.sort
               end
             else
               raise ValidationError, "list accepts dimensions or components"
             end
      @output.puts JSON.pretty_generate(Data.canonical(data))
      0
    end

    def explain
      parser = OptionParser.new
      parser.banner = "Usage: nexus-compose explain CAPABILITY [IMPLEMENTATION]"
      parser.parse!(@argv)
      capability = @argv.shift
      raise ValidationError, parser.banner unless capability
      implementations = @repository.catalog[capability]
      raise ValidationError, "unknown capability #{capability.inspect}" unless implementations

      implementation = @argv.shift
      raise ValidationError, "unexpected arguments: #{@argv.join(' ')}" unless @argv.empty?
      data = if implementation
               implementations[implementation] || raise(ValidationError, "unknown implementation #{capability}/#{implementation}")
             else
               implementations
             end
      clean = remove_internal_fields(Data.canonical(data))
      @output.puts Data.yaml(clean)
      0
    end

    def diff
      parser = OptionParser.new
      parser.banner = "Usage: nexus-compose diff LEFT_DIRECTORY RIGHT_DIRECTORY"
      parser.parse!(@argv)
      left = @argv.shift
      right = @argv.shift
      raise ValidationError, parser.banner unless left && right
      raise ValidationError, "unexpected arguments: #{@argv.join(' ')}" unless @argv.empty?

      left_lock = Data.load_yaml(File.join(left, "compose.lock.yaml"))
      right_lock = Data.load_yaml(File.join(right, "compose.lock.yaml"))
      differences = structural_diff(Data.canonical(left_lock), Data.canonical(right_lock))
      @output.puts JSON.pretty_generate("status" => differences.empty? ? "identical" : "different", "changes" => differences)
      differences.empty? ? 0 : 1
    end

    def structural_diff(left, right, path = "$", result = [])
      if left.is_a?(Hash) && right.is_a?(Hash)
        (left.keys | right.keys).sort.each do |key|
          structural_diff(left[key], right[key], "#{path}.#{key}", result)
        end
      elsif left.is_a?(Array) && right.is_a?(Array)
        maximum = [left.length, right.length].max
        maximum.times { |index| structural_diff(left[index], right[index], "#{path}[#{index}]", result) }
      elsif left != right
        result << {"path" => path, "left" => left, "right" => right}
      end
      result
    end

    def prompt(label, default = nil)
      suffix = default ? " [#{default}]" : ""
      @output.print "#{label}#{suffix}: "
      @output.flush
      value = @input.gets
      raise Error, "input ended while reading #{label}" unless value
      value = value.strip
      value.empty? ? default : value
    end

    def choose(label, values, default)
      raise ValidationError, "no choices available for #{label}" if values.empty?
      loop do
        value = prompt("#{label} (#{values.join('/')})", default)
        return value if values.include?(value)
        @output.puts "Choose one of: #{values.join(', ')}"
      end
    end

    def yes_no?(label, default)
      default_text = default ? "yes" : "no"
      loop do
        value = prompt("#{label} (yes/no)", default_text).downcase
        return true if %w[y yes].include?(value)
        return false if %w[n no].include?(value)
        @output.puts "Enter yes or no."
      end
    end

    def require_option!(options, key)
      raise ValidationError, "--#{key} is required" unless options[key]
    end

    def remove_internal_fields(value)
      case value
      when Hash
        value.each_with_object({}) do |(key, item), result|
          result[key] = remove_internal_fields(item) unless key.start_with?("_")
        end
      when Array
        value.map { |item| remove_internal_fields(item) }
      else
        value
      end
    end

    def help
      <<~HELP
        Nexus Composition Generator #{VERSION}

        Usage: nexus-compose COMMAND [OPTIONS]

        Commands:
          configure  Interactively create a reusable selection file
          plan       Resolve a selection without writing generated files
          generate   Create Compose and its deployment evidence package
          validate   Validate a generated Compose file or directory
          list       List dimensions or component implementations
          explain    Explain a component implementation
          diff       Compare two generated composition locks
          version    Print the generator version
          help       Show this help
      HELP
    end
  end
end
