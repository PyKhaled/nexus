# frozen_string_literal: true

require "fileutils"
require "tmpdir"

module SecretRepositoryFixture
  COMPOSITION_ROOT = File.expand_path("../../../../composition", __dir__)

  def with_secret_repository(website: nil, database: nil, composition_root: COMPOSITION_ROOT)
    Dir.mktmpdir("nexus-secret-fixture") do |root|
      # Copy only composition definitions; never copy developer environment files.
      Dir[File.join(composition_root, "**", "*.{yaml,yml}")].each do |source|
        relative = source.delete_prefix(composition_root + File::SEPARATOR)
        destination = File.join(root, "composition", relative)
        FileUtils.mkdir_p(File.dirname(destination))
        FileUtils.cp(source, destination)
      end
      {"system-website" => website, "system-website-db" => database}.each do |component, content|
        next if content.nil?

        destination = File.join(root, "system", component, ".env")
        FileUtils.mkdir_p(File.dirname(destination))
        File.write(destination, content)
      end
      yield NexusAssembler::Repository.new(root)
    end
  end
end
