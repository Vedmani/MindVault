<!-- TODO: Edit this to explain how to contribute to the project. How to setup the project locally, how to run tests, how to submit a pull request, etc.--> 
# Upgrading Editable Python Packages
## 🧑 human _(Aug 25, 2024, 02:16 PM)_
pip install -e '.[dev]' I have installed a package like this now, how can i upgrade it for a new release, with some changes in dev requirements
## 🤖 assistant _(Aug 25, 2024, 02:16 PM)_
 To upgrade a package that you've installed in editable mode (using `-e`) with some changes in the development requirements, you can follow these steps:

1. First, ensure you're in the directory of the package you want to upgrade.

2. Pull the latest changes from the repository (if it's version controlled):
   ```
   git pull
   ```

3. Then, you can upgrade the package using pip with the `--upgrade` or `-U` flag:
   ```
   pip install -U -e .[dev]
   ```

This command will:
- Reinstall the package in editable mode (`-e`)
- Upgrade all the dependencies to their latest versions that satisfy the requirements (`-U`)
- Install or upgrade any new or changed development dependencies (`[dev]`)

If you want to be more specific about which dependencies to upgrade, you can use the `--upgrade-strategy` option:

- To upgrade only the package itself and not its dependencies:
  ```
  pip install -U --upgrade-strategy eager -e .[dev]
  ```

- To upgrade the package and only the dependencies that need to be upgraded to satisfy new requirements:
  ```
  pip install -U --upgrade-strategy only-if-needed -e .[dev]
  ```

Remember that if there are significant changes in the package structure or build system, you might need to uninstall the old version first:

```
pip uninstall your-package-name
pip install -e .[dev]
```