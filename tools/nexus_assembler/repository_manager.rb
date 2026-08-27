# frozen_string_literal: true

require "fileutils"
require "open3"
require "tempfile"
require_relative "assembler"

module NexusAssembler
  GitResult = Struct.new(:stdout, :stderr, :success?, keyword_init: true)

  class RepositoryManager
    def initialize(repository = Repository.new, runner: nil)
      @repository = repository
      @runner = runner || method(:run_git)
    end

    def add(blueprint_path, name:, url:, path: nil, branch: nil, required: true)
      blueprint = load_blueprint(blueprint_path)
      declaration = {
        "name" => name,
        "url" => url,
        "path" => path || "system/#{name}",
        "required" => required
      }
      declaration["branch"] = branch if branch
      declarations = RepositoryDeclarations.validate(Array(blueprint["repositories"]) + [declaration])

      ensure_git_repository!
      ensure_path_available!(declaration.fetch("path"))
      arguments = ["submodule", "add"]
      arguments.concat(["--branch", branch]) if branch
      arguments.concat(["--", url, declaration.fetch("path")])
      git!(*arguments)

      blueprint["repositories"] = declarations
      atomic_write(blueprint_path, Data.yaml(blueprint))
      report_for(declaration)
    end

    def list(blueprint_path)
      declarations(blueprint_path).map { |declaration| report_for(declaration) }
    end

    def status(blueprint_path)
      reports = list(blueprint_path)
      required_failures = reports.reject do |report|
        !report.fetch("required") || report.fetch("status") == "initialized"
      end
      optional_failures = reports.reject do |report|
        report.fetch("required") || report.fetch("status") == "initialized"
      end
      overall_status = if required_failures.any?
                         "failed"
                       elsif optional_failures.any?
                         "passed-with-warnings"
                       else
                         "passed"
                       end
      {
        "status" => overall_status,
        "repositories" => reports
      }
    end

    def validate(blueprint_path)
      report = status(blueprint_path)
      failures = report.fetch("repositories").select do |repository|
        repository.fetch("required") && repository.fetch("status") != "initialized"
      end
      unless failures.empty?
        details = failures.map { |repository| "#{repository['name']}: #{repository['reason']}" }.join("; ")
        raise ValidationError, "repository validation failed: #{details}"
      end

      report
    end

    def sync(blueprint_path)
      ensure_git_repository!
      declarations(blueprint_path).each do |declaration|
        entry = gitmodules_by_path[declaration.fetch("path")]
        if entry
          validate_gitmodules_entry!(declaration, entry)
          next
        end

        ensure_path_available!(declaration.fetch("path"))
        arguments = ["submodule", "add"]
        arguments.concat(["--branch", declaration.fetch("branch")]) if declaration["branch"]
        arguments.concat(["--", declaration.fetch("url"), declaration.fetch("path")])
        git!(*arguments)
      end

      git!("submodule", "sync", "--recursive")
      git!("submodule", "update", "--init", "--recursive")
      validate(blueprint_path)
    end

    private

    def declarations(blueprint_path)
      blueprint = load_blueprint(blueprint_path)
      RepositoryDeclarations.validate(blueprint["repositories"])
    end

    def load_blueprint(blueprint_path)
      path = File.expand_path(blueprint_path)
      raise ValidationError, "blueprint file not found: #{path}" unless File.file?(path)

      blueprint = Data.load_yaml(path)
      raise ValidationError, "blueprint must be a mapping" unless blueprint.is_a?(Hash)

      blueprint
    end

    def report_for(declaration)
      path = declaration.fetch("path")
      entry = gitmodules_by_path[path]
      status, reason = repository_state(declaration, entry)
      declaration.merge("status" => status, "reason" => reason)
    end

    def repository_state(declaration, entry)
      return ["missing", "no matching entry in .gitmodules"] unless entry

      mismatch = gitmodules_mismatch(declaration, entry)
      return ["mismatch", mismatch] if mismatch

      absolute_path = File.join(@repository.root, declaration.fetch("path"))
      gitlink = gitlink_commit(declaration.fetch("path"))
      return ["not-a-submodule", "path is not recorded as a Gitlink in the parent repository"] unless gitlink
      return ["uninitialized", "submodule working tree is absent"] unless File.directory?(absolute_path)

      top_level = git_in_path(absolute_path, "rev-parse", "--show-toplevel")
      unless top_level && canonical_path(top_level.strip) == canonical_path(absolute_path)
        return ["not-a-submodule", "path exists but is not an initialized Git submodule"]
      end

      checkout = git_in_path(absolute_path, "rev-parse", "HEAD")&.strip
      unless checkout == gitlink
        return ["checkout-mismatch", "checked out commit #{checkout.inspect} does not match Gitlink #{gitlink}"]
      end

      ["initialized", "configured and checked out"]
    end

    def validate_gitmodules_entry!(declaration, entry)
      mismatch = gitmodules_mismatch(declaration, entry)
      raise ValidationError, "#{declaration['name']} conflicts with .gitmodules: #{mismatch}" if mismatch
    end

    def gitmodules_mismatch(declaration, entry)
      return "URL is #{entry['url'].inspect}, expected #{declaration['url'].inspect}" if entry["url"] != declaration["url"]
      if declaration["branch"] && entry["branch"] != declaration["branch"]
        return "branch is #{entry['branch'].inspect}, expected #{declaration['branch'].inspect}"
      end

      nil
    end

    def gitmodules_by_path
      path = File.join(@repository.root, ".gitmodules")
      return {} unless File.file?(path)

      entries = {}
      current = nil
      File.foreach(path) do |line|
        if line =~ /^\s*\[submodule\s+"([^"]+)"\]\s*$/
          current = {"name" => Regexp.last_match(1)}
        elsif current && line =~ /^\s*(path|url|branch)\s*=\s*(.*?)\s*$/
          current[Regexp.last_match(1)] = Regexp.last_match(2)
          entries[current.fetch("path")] = current if current["path"]
        end
      end
      entries
    end

    def ensure_git_repository!
      git!("rev-parse", "--show-toplevel")
    end

    def ensure_path_available!(relative_path)
      absolute_path = File.join(@repository.root, relative_path)
      return unless File.exist?(absolute_path)

      raise ValidationError, "repository path already exists: #{relative_path}"
    end

    def git!(*arguments)
      result = @runner.call(*arguments)
      return result if result.success?

      detail = result.stderr.to_s.strip
      detail = result.stdout.to_s.strip if detail.empty?
      raise Error, "git #{arguments.join(' ')} failed#{detail.empty? ? '' : ": #{detail}"}"
    end

    def git_in_path(path, *arguments)
      stdout, _stderr, status = Open3.capture3("git", "-C", path, *arguments)
      status.success? ? stdout : nil
    end

    def gitlink_commit(relative_path)
      stdout, _stderr, status = Open3.capture3(
        "git", "-C", @repository.root, "ls-files", "--stage", "--", relative_path
      )
      return nil unless status.success?

      match = stdout.match(/\A160000\s+([0-9a-f]{40,64})\s+\d+\t/)
      match && match[1]
    end

    def canonical_path(path)
      File.realpath(path)
    rescue Errno::ENOENT
      File.expand_path(path)
    end

    def run_git(*arguments)
      stdout, stderr, status = Open3.capture3("git", "-C", @repository.root, *arguments)
      GitResult.new(stdout: stdout, stderr: stderr, success?: status.success?)
    end

    def atomic_write(path, content)
      destination = File.expand_path(path)
      FileUtils.mkdir_p(File.dirname(destination))
      temporary = Tempfile.new([".#{File.basename(destination)}", ".tmp"], File.dirname(destination))
      begin
        temporary.write(content)
        temporary.flush
        temporary.fsync
        temporary.close
        File.rename(temporary.path, destination)
      ensure
        temporary.close unless temporary.closed?
        temporary.unlink if File.exist?(temporary.path)
      end
    end
  end
end
