# frozen_string_literal: true

require "minitest/autorun"
require "fileutils"
require "tmpdir"
require_relative "../repository_manager"

class NexusAssemblerRepositoryManagerTest < Minitest::Test
  def test_add_declares_and_clones_a_real_submodule
    with_git_repositories do |root, child, blueprint|
      manager = manager_with_local_protocol(root)

      report = manager.add(
        blueprint,
        name: "system-service",
        url: child,
        branch: "main"
      )

      assert_equal "initialized", report.fetch("status")
      assert File.file?(File.join(root, ".gitmodules"))
      assert File.directory?(File.join(root, "system/system-service/.git")) ||
             File.file?(File.join(root, "system/system-service/.git"))
      declared = NexusAssembler::Data.load_yaml(blueprint).fetch("repositories").first
      assert_equal "system/system-service", declared.fetch("path")
      assert_equal child, declared.fetch("url")
      assert_equal "passed", manager.validate(blueprint).fetch("status")
    end
  end

  def test_sync_materializes_declared_repositories
    with_git_repositories do |root, child, blueprint|
      write_blueprint(
        blueprint,
        [repository_declaration(child)]
      )
      manager = manager_with_local_protocol(root)

      report = manager.sync(blueprint)

      assert_equal "passed", report.fetch("status")
      assert_equal "initialized", report.fetch("repositories").first.fetch("status")
    end
  end

  def test_validate_rejects_a_required_missing_repository
    Dir.mktmpdir("nexus-repository-manager") do |root|
      initialize_git(root)
      blueprint = File.join(root, "nexus.yaml")
      write_blueprint(
        blueprint,
        [repository_declaration("https://example.com/system-service.git")]
      )
      manager = NexusAssembler::RepositoryManager.new(NexusAssembler::Repository.new(root))

      error = assert_raises(NexusAssembler::ValidationError) { manager.validate(blueprint) }

      assert_includes error.message, "no matching entry in .gitmodules"
    end
  end

  def test_validate_allows_an_optional_missing_repository
    Dir.mktmpdir("nexus-repository-manager") do |root|
      initialize_git(root)
      blueprint = File.join(root, "nexus.yaml")
      declaration = repository_declaration("https://example.com/optional.git").merge("required" => false)
      write_blueprint(blueprint, [declaration])
      manager = NexusAssembler::RepositoryManager.new(NexusAssembler::Repository.new(root))

      report = manager.validate(blueprint)

      assert_equal "passed-with-warnings", report.fetch("status")
      assert_equal "missing", report.fetch("repositories").first.fetch("status")
    end
  end

  def test_validate_detects_url_drift
    with_git_repositories do |root, child, blueprint|
      manager = manager_with_local_protocol(root)
      manager.add(blueprint, name: "system-service", url: child, branch: "main")
      document = NexusAssembler::Data.load_yaml(blueprint)
      document.fetch("repositories").first["url"] = "https://example.com/other.git"
      File.write(blueprint, NexusAssembler::Data.yaml(document))

      error = assert_raises(NexusAssembler::ValidationError) { manager.validate(blueprint) }

      assert_includes error.message, "expected \"https://example.com/other.git\""
    end
  end

  private

  def with_git_repositories
    Dir.mktmpdir("nexus-repository-parent") do |root|
      Dir.mktmpdir("nexus-repository-child") do |child|
        initialize_git(child)
        File.write(File.join(child, "README.md"), "# Child\n")
        git!(child, "add", "README.md")
        git!(child, "commit", "-m", "Initial child")

        initialize_git(root)
        FileUtils.mkdir_p(File.join(root, "system"))
        blueprint = File.join(root, "nexus.yaml")
        write_blueprint(blueprint, [])
        git!(root, "add", "nexus.yaml")
        git!(root, "commit", "-m", "Initial parent")

        yield root, child, blueprint
      end
    end
  end

  def initialize_git(path)
    git!(path, "init", "--initial-branch=main")
    git!(path, "config", "user.name", "Nexus Test")
    git!(path, "config", "user.email", "nexus@example.test")
  end

  def manager_with_local_protocol(root)
    runner = lambda do |*arguments|
      stdout, stderr, status = Open3.capture3(
        "git", "-C", root, "-c", "protocol.file.allow=always", *arguments
      )
      NexusAssembler::GitResult.new(stdout: stdout, stderr: stderr, success?: status.success?)
    end
    NexusAssembler::RepositoryManager.new(NexusAssembler::Repository.new(root), runner: runner)
  end

  def repository_declaration(url)
    {
      "name" => "system-service",
      "url" => url,
      "path" => "system/system-service",
      "branch" => "main",
      "required" => true
    }
  end

  def write_blueprint(path, repositories)
    File.write(
      path,
      NexusAssembler::Data.yaml(
        "apiVersion" => "nexus.io/composition/v1alpha1",
        "product" => {"name" => "test", "edition" => "custom"},
        "deployment" => {
          "target" => "local",
          "environment" => "development",
          "assurance" => "standard"
        },
        "capabilities" => {},
        "repositories" => repositories
      )
    )
  end

  def git!(path, *arguments)
    _stdout, stderr, status = Open3.capture3("git", "-C", path, *arguments)
    raise "git #{arguments.join(' ')} failed: #{stderr}" unless status.success?
  end
end
