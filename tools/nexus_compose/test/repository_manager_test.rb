# frozen_string_literal: true

require "minitest/autorun"
require "fileutils"
require "tmpdir"
require_relative "../repository_manager"

class NexusComposeRepositoryManagerTest < Minitest::Test
  def test_add_declares_and_clones_a_real_submodule
    with_git_repositories do |root, child, selection|
      manager = manager_with_local_protocol(root)

      report = manager.add(
        selection,
        name: "system-service",
        url: child,
        branch: "main"
      )

      assert_equal "initialized", report.fetch("status")
      assert File.file?(File.join(root, ".gitmodules"))
      assert File.directory?(File.join(root, "system/system-service/.git")) ||
             File.file?(File.join(root, "system/system-service/.git"))
      declared = NexusCompose::Data.load_yaml(selection).fetch("repositories").first
      assert_equal "system/system-service", declared.fetch("path")
      assert_equal child, declared.fetch("url")
      assert_equal "passed", manager.validate(selection).fetch("status")
    end
  end

  def test_sync_materializes_declared_repositories
    with_git_repositories do |root, child, selection|
      write_selection(
        selection,
        [repository_declaration(child)]
      )
      manager = manager_with_local_protocol(root)

      report = manager.sync(selection)

      assert_equal "passed", report.fetch("status")
      assert_equal "initialized", report.fetch("repositories").first.fetch("status")
    end
  end

  def test_validate_rejects_a_required_missing_repository
    Dir.mktmpdir("nexus-repository-manager") do |root|
      initialize_git(root)
      selection = File.join(root, "nexus.yaml")
      write_selection(
        selection,
        [repository_declaration("https://example.com/system-service.git")]
      )
      manager = NexusCompose::RepositoryManager.new(NexusCompose::Repository.new(root))

      error = assert_raises(NexusCompose::ValidationError) { manager.validate(selection) }

      assert_includes error.message, "no matching entry in .gitmodules"
    end
  end

  def test_validate_allows_an_optional_missing_repository
    Dir.mktmpdir("nexus-repository-manager") do |root|
      initialize_git(root)
      selection = File.join(root, "nexus.yaml")
      declaration = repository_declaration("https://example.com/optional.git").merge("required" => false)
      write_selection(selection, [declaration])
      manager = NexusCompose::RepositoryManager.new(NexusCompose::Repository.new(root))

      report = manager.validate(selection)

      assert_equal "passed-with-warnings", report.fetch("status")
      assert_equal "missing", report.fetch("repositories").first.fetch("status")
    end
  end

  def test_validate_detects_url_drift
    with_git_repositories do |root, child, selection|
      manager = manager_with_local_protocol(root)
      manager.add(selection, name: "system-service", url: child, branch: "main")
      document = NexusCompose::Data.load_yaml(selection)
      document.fetch("repositories").first["url"] = "https://example.com/other.git"
      File.write(selection, NexusCompose::Data.yaml(document))

      error = assert_raises(NexusCompose::ValidationError) { manager.validate(selection) }

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
        selection = File.join(root, "nexus.yaml")
        write_selection(selection, [])
        git!(root, "add", "nexus.yaml")
        git!(root, "commit", "-m", "Initial parent")

        yield root, child, selection
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
      NexusCompose::GitResult.new(stdout: stdout, stderr: stderr, success?: status.success?)
    end
    NexusCompose::RepositoryManager.new(NexusCompose::Repository.new(root), runner: runner)
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

  def write_selection(path, repositories)
    File.write(
      path,
      NexusCompose::Data.yaml(
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
