# Scanner Configuration

The active security starter invokes Trivy through its pinned GitHub Action. Workflow inputs explicitly choose filesystem vulnerability/misconfiguration scanning and SARIF output. Container publishing uses image scanning instead.

`templates/configuration/scanners/trivy.yaml` is an optional CLI configuration example; copying it does not activate it in the workflow. Wire any custom configuration into the scanner invocation explicitly and check its resolved settings in a trial run.

Shared pre-commit configuration contains file hygiene and private-key checks without references to absent stack-specific files. It does not replace the security workflow or a comprehensive secret scanner.

Advanced Semgrep, Gitleaks, ZAP, and other imported configurations remain in the archive. Port one tool at a time: define the tool's requirements, input paths, supported report format, failure handling, network behavior, and synthetic verification case. Do not assume that copying an old rule file enables a scanner.

Scanner operational failures must fail the job. A valid empty report is different from no report. Keep evidence validation in place before the tolerant report importer.
