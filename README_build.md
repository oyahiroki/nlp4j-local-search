# Build and Release Notes

This document describes how to build and release `nlp4j-local-search` to PyPI.

This is a maintainer-oriented memo for future releases.

## Prerequisites

This document assumes that the following items are already prepared.

* A PyPI account
* A PyPI API token
* Optionally, a TestPyPI account and a TestPyPI API token
* Python environment for building packages
* The repository is already cloned locally
* `pyproject.toml` is already configured
* `README.md` and `LICENSE` are included in the repository

Do not write API tokens directly in this file or commit them to Git.

## Package name

The PyPI package name is:

```text
nlp4j-local-search
```

The Python import package name is:

```python
import nlp4j_local_search
```

## Release version

Update the version in `pyproject.toml`.

Example:

```toml
[project]
name = "nlp4j-local-search"
version = "0.4.0"
```

Important:

* Once a version is uploaded to PyPI, the same version file cannot be overwritten.
* If a release needs to be fixed, increment the version, for example from `0.2.0` to `0.2.1`.


## Update README.md

Before building a new release, update `README.md` to reflect the new version.

Check at least the following items:

* Update the current version number.
* Update installation examples such as `pip install nlp4j-local-search==0.5.0`.
* Update examples or feature descriptions if the release adds or changes APIs.
* Check that the information shown on the PyPI project page will be up to date.

If `README_ja.md` contains version-specific information, update it as well.

The README should be updated before running `python -m build`, because the packaged metadata may use it as the project description shown on PyPI.

## Install build tools

From the repository root:

```bash
python -m pip install --upgrade pip
python -m pip install --upgrade build twine
```

## Clean previous build files

Before building a new release, remove old build artifacts.

```bash
rm -rf dist build *.egg-info src/*.egg-info
```

## Build the package

```bash
python -m build
```

Expected output example:

```text
Successfully built nlp4j_local_search-0.4.0.tar.gz and nlp4j_local_search-0.4.0-py3-none-any.whl
```

The generated files are placed under `dist/`.

Example:

```text
dist/
  nlp4j_local_search-0.4.0.tar.gz
  nlp4j_local_search-0.4.0-py3-none-any.whl
```

## Check the package

Run `twine check`.

```bash
python -m twine check dist/*
```

Expected output example:

```text
Checking dist/nlp4j_local_search-0.4.0-py3-none-any.whl: PASSED
Checking dist/nlp4j_local_search-0.4.0.tar.gz: PASSED
```

## Check package size

Because this package includes Java JAR files, check the generated file size.

```bash
ls -lh dist
```

## Check that JAR files are included

Check the wheel contents.

```bash
unzip -l dist/*.whl | grep jar
```

Expected result:

```text
nlp4j_local_search/jars/...
```

If JAR files are not included, check `pyproject.toml`.

Example:

```toml
[tool.setuptools.package-data]
nlp4j_local_search = ["jars/*.jar"]
```

## Local installation test

Create a temporary virtual environment and install the generated wheel.

```bash
python -m venv .venv-release-test
source .venv-release-test/bin/activate

python -m pip install --upgrade pip
python -m pip install dist/nlp4j_local_search-0.4.0-py3-none-any.whl
```

Check that the package can be imported and basic search works.

```bash
python - <<'PY'
import nlp4j_local_search
from nlp4j_local_search import SearchEngine

# Keyword search smoke test
with SearchEngine("en") as engine:
    engine.add_json({"id": "1", "body": "Kyoto is a historic city.", "category": "city"})
    engine.add_json({"id": "2", "body": "Nintendo is a company.",    "category": "company"})
    engine.commit()

    # Basic keyword search
    results = engine.search("Kyoto", limit=10)
    assert len(results) == 1, f"Expected 1, got {len(results)}"

    # Field filtering
    results = engine.search("", limit=10, filters={"category": "city"})
    assert len(results) == 1, f"Expected 1, got {len(results)}"

print("smoke test passed")
PY
```

After the test:

```bash
deactivate
rm -rf .venv-release-test
```

## Optional: upload to TestPyPI

If you want to test the upload before publishing to the production PyPI, upload to TestPyPI.

```bash
python -m twine upload --repository testpypi dist/*
```

When prompted, enter:

```text
username: __token__
password: <TestPyPI API token>
```

Important:

* A PyPI token from `pypi.org` cannot be used for TestPyPI.
* Use a token created on TestPyPI.
* TestPyPI and PyPI are separate services.

### Install from TestPyPI

Create a new virtual environment.

```bash
python -m venv .venv-testpypi
source .venv-testpypi/bin/activate

python -m pip install --upgrade pip
```

Install dependencies from the normal PyPI if needed.

```bash
python -m pip install jpype1
```

Install the package from TestPyPI.

```bash
python -m pip install \
  --index-url https://test.pypi.org/simple/ \
  --no-deps \
  nlp4j-local-search==0.4.0
```

Check import.

```bash
python - <<'PY'
import nlp4j_local_search
print(nlp4j_local_search)
PY
```

After the test:

```bash
deactivate
rm -rf .venv-testpypi
```

## Upload to PyPI

Upload to the production PyPI.

```bash
python -m twine upload dist/*
```

When prompted, enter:

```text
username: __token__
password: <PyPI API token>
```

The API token value usually starts with:

```text
pypi-
```

Do not paste your normal PyPI login password.

## Check the published package

After upload, check the PyPI project page.

```text
https://pypi.org/project/nlp4j-local-search/
```

You can also check a specific version.

```text
https://pypi.org/project/nlp4j-local-search/0.4.0/
```

```bash
python -m pip index versions nlp4j-local-search \
  --no-cache-dir \
  --index-url https://pypi.org/simple
```


## Install from PyPI

Create a clean virtual environment.

```bash
python -m venv .venv-pypi-test
source .venv-pypi-test/bin/activate

python -m pip install --upgrade pip
python -m pip install nlp4j-local-search==0.4.0
```

Check installation.

```bash
python -m pip show nlp4j-local-search
```

Check import.

```bash
python - <<'PY'
import nlp4j_local_search
print(nlp4j_local_search)
PY
```

After the test:

```bash
deactivate
rm -rf .venv-pypi-test
```

## Git commit and tag

After confirming that the release was successful, commit the release changes.

```bash
git status
git add pyproject.toml \
        README.md README_ja.md README_build.md README_verup.md \
        src/nlp4j_local_search/engine.py \
        src/nlp4j_local_search/jars/nlp4j-localsearch.jar \
        examples/example_003_field_search.py \
        examples/example_004_keyword_and_field_search.py \
        examples/example_005_vector_and_field_search.py \
        tests/test_field_search.py
git commit -m "Release v0.4.0"
```

Create a Git tag.

```bash
git tag v0.4.0
git push origin main
git push origin v0.4.0
```

## Full command example

Replace `0.4.0` with the actual release version.

```bash
# Install build tools
python -m pip install --upgrade pip
python -m pip install --upgrade build twine

# Clean
rm -rf dist build *.egg-info src/*.egg-info

# Build
python -m build

# Check
python -m twine check dist/*
ls -lh dist
unzip -l dist/*.whl | grep jar

# Upload to PyPI
python -m twine upload dist/*
```

## Troubleshooting

### 403 Forbidden when uploading to TestPyPI

Possible cause:

* A production PyPI token was used for TestPyPI.

Solution:

* Create and use a TestPyPI API token.
* TestPyPI and PyPI require separate tokens.

### 403 Forbidden when uploading to PyPI

Possible causes:

* The username is not `__token__`.
* The API token is incorrect.
* The token does not have permission for the project.

Solution:

* Use `__token__` as the username.
* Use the full API token as the password, including the `pypi-` prefix.
* If the project already exists, check that the token has permission for the project.

### File already exists

Possible cause:

* The same version was already uploaded to PyPI.

Solution:

* Increment the version in `pyproject.toml`.
* Rebuild the package.
* Upload the new version.

Example:

```toml
version = "0.3.1"
```

### License classifier error

Error example:

```text
License classifiers have been superseded by license expressions
```

Possible cause:

* `License :: OSI Approved :: Apache Software License` remains in `classifiers`.

Solution:

Use SPDX license expression in `pyproject.toml`.

```toml
license = "Apache-2.0"
license-files = ["LICENSE"]
```

Remove the old license classifier.

```toml
# Remove this:
# "License :: OSI Approved :: Apache Software License"
```

### JAR files are missing from the wheel

Check the wheel.

```bash
unzip -l dist/*.whl | grep jar
```

If no JAR files are shown, check `pyproject.toml`.

```toml
[tool.setuptools.package-data]
nlp4j_local_search = ["jars/*.jar"]
```

Then clean and rebuild.

```bash
rm -rf dist build *.egg-info src/*.egg-info
python -m build
```

## Notes

* Keep API tokens secret.
* Do not commit `.pypirc` if it contains tokens.
* Do not reuse a version number after uploading to PyPI.
* Always test installation in a clean virtual environment.
* Check that the wheel includes the required JAR files before publishing.


