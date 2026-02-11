---
paths:
  - "scripts/**/*.py"
---

# Python Rules

- Python 3.9+ compatible (use `from __future__ import annotations` for type hints)
- No external dependencies beyond stdlib when possible
- Use `urllib` over `requests` for HTTP
- Environment variables for secrets, never hardcode
