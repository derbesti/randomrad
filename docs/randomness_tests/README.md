# randomness_testsuite integration

We use `stevenang/randomness_testsuite` as a Python-based randomness test library.
The repository is NOT pip-installable, so it is included as a git submodule.

## Add submodule (once)

```bash
git submodule add https://github.com/stevenang/randomness_testsuite.git external/randomness_testsuite
git submodule update --init --recursive