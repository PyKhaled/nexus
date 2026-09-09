# frozen_string_literal: true
# Requires Ruby (already used by Assembler tests) and the Docker Compose CLI.
# Resolves models only; never starts containers or reads checkout credentials.
require 'json'
require 'tmpdir'
require 'fileutils'
require 'open3'

root = File.expand_path('../..', __dir__)
Dir.mktmpdir('nexus-config') do |dir|
  %w[compose.yml compose.config.yml compose.secrets.yml makefile scripts/config.sh
     config/compose/config.env.example config/compose/secret.env.example
     system/system-auth/.env.example system/system-auth-db/.env.example].each do |path|
    destination = File.join(dir, path)
    FileUtils.mkdir_p(File.dirname(destination))
    FileUtils.cp(File.join(root, path), destination)
  end
  runtime = File.join(dir, 'private config')
  FileUtils.mkdir_p(runtime)
  config = "MYSQL_DATABASE=example\nKC_DB_USERNAME=example\nPOSTGRES_USER=example\n"
  secrets = "MYSQL_PASSWORD=literal $dollar # password\nMYSQL_ROOT_PASSWORD=admin-only\n" \
            "KC_DB_PASSWORD=auth-password\nPOSTGRES_PASSWORD=auth-password\nKENER_SECRET_KEY=status-only\n"
  File.write(File.join(runtime, 'config.env'), config)
  File.write(File.join(runtime, 'secret.env'), secrets)
  File.chmod(0600, *Dir[File.join(runtime, '*.env')])
  env = {'NEXUS_CONFIG_DIR' => runtime, 'NEXUS_ENV' => 'development',
         'SECRETS_ENV' => File.join(dir, 'absent'), 'COMPOSE_FILE' => nil,
         'COMPOSE_SECRETS' => nil}
  (config + secrets).lines.each { |line| env[line.split('=').first] = nil }
  run = lambda do |*command|
    out, err, status = Open3.capture3(env, *command, chdir: dir)
    raise "Command failed: #{command.join(' ')}\n#{err}" unless status.success?
    out
  end
  run.call('make', '-s', 'config-check', 'compose-check')
  model = lambda do |overlay|
    files = %w[compose.yml compose.config.yml] + overlay
    args = files.flat_map { |file| ['-f', file] }
    JSON.parse(run.call('bash', 'scripts/config.sh', 'run', '--', 'docker', 'compose',
                        '--env-file', '/dev/null', *args, 'config', '--format', 'json'))
  end
  services = model.call([]).fetch('services')
  # Compose serializes literal dollars as $$ so rendered models can be reloaded.
  raise 'password changed' unless services['website']['environment']['WORDPRESS_DB_PASSWORD'] == 'literal $$dollar # password'
  raise 'shared password mismatch' unless services['website-db']['environment']['MYSQL_PASSWORD'] == services['website']['environment']['WORDPRESS_DB_PASSWORD']
  raise 'auth mapping missing' unless services['keycloak']['environment']['KC_DB_PASSWORD'] == 'auth-password'
  raise 'postgres mapping missing' unless services['keycloak-db']['environment']['POSTGRES_PASSWORD'] == 'auth-password'
  raise 'admin secret reached website' if services['website']['environment'].key?('MYSQL_ROOT_PASSWORD')
  raise 'unrelated secret reached gateway' if services['gateway']['environment'].key?('KENER_SECRET_KEY')
  %w[mysql_password mysql_root_password].each { |name| File.write(File.join(runtime, name), 'synthetic') }
  File.open(File.join(runtime, 'config.env'), 'a') do |file|
    file.puts "MYSQL_PASSWORD_FILE=#{runtime}/mysql_password"
    file.puts "MYSQL_ROOT_PASSWORD_FILE=#{runtime}/mysql_root_password"
  end
  run.call('make', '-s', 'compose-check', 'COMPOSE_SECRETS=compose.secrets.yml')
  services = model.call(['compose.secrets.yml']).fetch('services')
  raise 'password environment survived overlay' if services['website']['environment'].key?('WORDPRESS_DB_PASSWORD') || services['website-db']['environment'].key?('MYSQL_PASSWORD') || services['website-db']['environment'].key?('MYSQL_ROOT_PASSWORD')
  grants = services['website'].fetch('secrets').map { |secret| secret.fetch('source') }
  raise 'website secret grants incorrect' unless grants == ['mysql_password']
  _, _, status = Open3.capture3(env, 'make', '-s', 'compose-check', 'ENV=production', chdir: dir)
  raise 'production accepted development model' if status.success?
end
puts 'Compose configuration and secret-isolation tests passed.'
