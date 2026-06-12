Pipeline runner and smoke tests

Usage
- PowerShell (Windows):

  Open PowerShell at workspace root and run:

  ```powershell
  .\sample_idea_1\gov-scheme-navigator\scripts\pipeline_runner.ps1
  ```

- Bash (Linux/macOS or WSL):

  ```bash
  ./sample_idea_1/gov-scheme-navigator/scripts/pipeline_runner.sh
  ```

Behavior
- Runs backend unit tests
- Applies alembic migrations (if present)
- Starts backend and waits for readiness
- Runs smoke/integration tests
- Builds frontend (if present)
- Brings up `docker compose` for the project and runs container smoke tests

Logs
- Files are written to `gov-scheme-navigator/pipeline_log.txt` and step-specific logs in the `gov-scheme-navigator` folder.

Notes
- The scripts assume `python`, `pip`, `npm`, `alembic`, and `docker` are available on PATH.
- Adjust ports or paths by editing the scripts.
