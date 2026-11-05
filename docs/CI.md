# Continuous integration

The GitHub Actions workflow at `.github/workflows/tests.yml` runs the offline unit and integration suite on pushes and pull requests targeting `main`.

The workflow tests Python 3.10, 3.11, 3.12, and 3.13, then performs a CLI smoke test. It requires no API keys or third-party runtime dependencies.

View executions in the repository's Actions tab:
https://github.com/Sachhin/ORACLE/actions
