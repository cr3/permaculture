Python Template
===============

Repository template to bootstrap a Python project.

Benefits of this template
-------------------------

* Installs the expected Python version under ``.venv/``.
* Installs Python dependencies also under ``.venv/``.
* Pins dependency versions in ``poetry.lock``.
* Provides default template for pull requests.
* Checks for syntax and format on pull requests.
* Runs tests on pull requests.
* Pushes documentation to GitHub pages also when creating tags.
* Includes settings for editors and some specifically for VSCode.

Creating a new repository
-------------------------

To create the repository for a new project:

1. On `GitHub`_, navigate to the main page of this repository.
2. Above the file list, click *Use this template*.
3. Select *Create a new repository*.
4. Follow the usual steps.

.. _GitHub: https://github.com/cr3

Configuring the new repository
------------------------------

In GitHub -> Settings:

1. General:

   * Uncheck ``Wikis``
   * Uncheck ``Projects``
   * Check ``Automatically delete head branches``

2. Branch protection rules:

   * Branch name pattern: ``main``
   * Check ``Require a pull request before merging``
   * Check ``Require review from Code Owners``
   * Check ``Require status checks to pass before merging``
   * Click on ``Create``

3. Another branch protection rules:

   * Branch name pattern: ``gh-pages``
   * Check ``Allow force pushes``
   * Click on ``Create``

4. Create branch named ``gh-pages``.

In the source:

1. Rewrite this ``README.md``.
2. Update the ``LICENSE.rst``.
3. Replace "changeme" with your project details in:

   * ``docs/api.rst``
   * ``docs/conf.py``
   * ``docs/modules.rst``
   * ``pyproject.toml``
   * ``CONTRIBUTING.rst``

4. Rename the directory "changeme" with your project name.

Using the new repository
------------------------

1. ``make setup`` to setup the Python environment with ``conda`` and install the poetry environment.
2. ``make check`` to check syntax and formatting.
3. ``make test`` to run tests.
4. ``make docs`` to build documentation - requires first running ``poetry install --with docs``.
5. ``poetry add [package]`` to install ``[package]`` in ``.venv/``, add it in ``pyproject.toml`` and pin its version in ``poetry.lock``.

Maintaining the new repository
------------------------------

1. In the new repository, add the remote template repository - only needs to be done once:

   .. code-block:: text

      > git remote add template https://github.com/cr3/python-template.git

2. Fetch the latest changes and review the log:

   .. code-block:: text

      > git fetch template
      > git log template/main
      ...

3. Cherry pick each revision from the above log command:

   .. code-block:: text

      > git cherry-pick [revno]


References
----------

* `Creating a repository from a template <https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-repository-from-a-template>`__
