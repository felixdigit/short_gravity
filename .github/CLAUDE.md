# MICROKERNEL: GITHUB ACTIONS
You are working in the GitHub Actions workflow directory.

YOUR LAWS OF PHYSICS:
1. YAML ONLY: Workflow files are YAML (`.yml`). Do not create scripts here — scripts live in `scripts/data-fetchers/`.
2. SECRETS ONLY: All credentials must use `${{ secrets.VARIABLE_NAME }}` syntax. Never hardcode API keys or tokens.
3. SCRIPT PATHS: All Python scripts are at `scripts/data-fetchers/<name>.py` relative to the repo root.
4. STANDARD ACTIONS: Use `actions/checkout@v4` and `actions/setup-python@v5`. Keep action versions current.
5. MANUAL TRIGGER: Every workflow must include `workflow_dispatch:` to allow manual triggering in addition to cron schedules.
