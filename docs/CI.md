# Continuous integration

The GitHub Actions workflow at `.github/workflows/tests.yml` runs the offline unit and integration suite on pushes and pull requests targeting `main`.

The Python matrix covers Python 3.10 through 3.14. Each version runs the full offline unit/integration suite, builds and installs the package, and performs an installed-CLI smoke test outside the source tree. These checks require no API keys.

A separate live R/Bioconductor job installs edgeR and limma and runs the reference integration checks. This job verifies the optional statistical adapters against the installed Bioconductor implementation; it does not replace independent external-dataset validation.

View executions in the repository's Actions tab:
https://github.com/Sachhin/ORACLE/actions
