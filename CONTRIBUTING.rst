How to contribute
=================

Thank you for thinking of contributing!


Reporting issues
----------------

Include the following information in your post:

-   Describe what you expected to happen.
-   If possible, include a `minimal reproducible example`_ to help us
    identify the issue. This also helps check that the issue is not with
    your own code.
-   Describe what actually happened. Include the full traceback if there
    was an exception.
-   List your Python and other versions. If possible, check if this
    issue is already fixed in the latest releases or the latest code in
    the repository.

.. _minimal reproducible example: https://stackoverflow.com/help/minimal-reproducible-example


Submitting patches
------------------

If there is not an open issue for what you want to submit, prefer
opening one for discussion before working on a PR. You can work on any
issue that doesn't have an open PR linked to it or a maintainer assigned
to it. These show up in the sidebar. No need to ask if you can work on
an issue that interests you.

Include the following in your patch:

-   Use `Black`_ to format your code. This and other tools will run
    automatically if you install `pre-commit`_ using the instructions
    below.
-   Include tests if your patch adds or changes code. Make sure the test
    fails without your patch.
-   Update any relevant docs pages and docstrings. Docs pages and
    docstrings should be wrapped at 72 characters.
-   Add an entry in ``CHANGES.rst``. Use the same style as other
    entries. Also include ``.. versionchanged::`` inline changelogs in
    relevant docstrings.

.. _Black: https://black.readthedocs.io
.. _pre-commit: https://pre-commit.com


Setting up
----------

-   Download and install:

    - `Git`_
    - `Miniconda`_ - Check the box "Add to PATH environment variable"

-   Make sure you have a `GitHub account`_.
-   Configure git with your `username`_ and `email`_.

    .. code-block:: text

        > git config --global user.name "<your full name>""
        > git config --global user.email <your email address>

-   `Generate new token (classic)`_

    - Expiration: No expiration
    - Permissions: "repo" and "workflow"

-   Configure git with your token:

    .. code-block:: text

        > git config --global credential.helper manager
        > git clone https://github.com/cr3/python-template
        Cloning into 'python-template'...

    - Select "manager"
    - Check "Always use this from now on" and press "Select"
    - Sign in with token and paste your token

-   `Clone`_ the main repository locally.

    .. code-block:: text

        > git clone https://github.com/cr3/changeme
        > cd changeme

-   Create a virtualenv.

    .. code-block:: text

        > make setup

.. _git: https://git-scm.com/download/win
.. _miniconda: https://repo.anaconda.com/miniconda/Miniconda3-latest-Windows-x86_64.exe
.. _username: https://docs.github.com/en/github/using-git/setting-your-username-in-git
.. _email: https://docs.github.com/en/github/setting-up-and-managing-your-github-user-account/setting-your-commit-email-address
.. _GitHub account: https://github.com/join
.. _Generate new token (classic): https://github.com/settings/tokens
.. _Clone: https://docs.github.com/en/github/getting-started-with-github/fork-a-repo#step-2-create-a-local-clone-of-your-fork


Troubleshooting
---------------

-   .. code-block:: text

        Solving environment: failed

        ResolvePackageNotFound:
          - python=3.11

    The cache is probably corrupt - run ``conda clean -a``.

Starting to code
----------------

-   Create a branch to identify the issue you would like to work on.

    .. code-block:: text

        > git fetch origin
        > git checkout -b <your branch name> origin/main

-   Using your favorite editor, make your changes,
    `committing as you go`_.
-   Include tests that cover any code changes you make. Make sure the
    test fails without your patch. Run the tests as described below.
-   Push your commits to your branch on GitHub and
    `create a pull request`_. Link to the issue being addressed with
    ``fixes #123`` in the pull request.

    .. code-block:: text

        > git push origin <your branch name>

.. _committing as you go: https://afraid-to-commit.readthedocs.io/en/latest/git/commandlinegit.html#commit-your-changes
.. _create a pull request: https://docs.github.com/en/github/collaborating-with-issues-and-pull-requests/creating-a-pull-request


Running the tests
-----------------

Run the basic test suite with pytest:

.. code-block:: text

    > make test


Checking the syntax
-------------------

Check syntax with ``black`` and ``ruff``:

.. code-block:: text

    > poetry install --with check
    > make check


Building the docs
-----------------

Build the docs in the ``docs`` directory using Sphinx:

.. code-block:: text

    > poetry install --with docs
    > make docs

Update the apidoc when adding new modules:

.. code-block:: text

    > sphinx-apidoc --force --implicit-namespaces -o docs changeme

Open ``build/html/index.html`` in your browser to view the docs.

Read more about `Sphinx <https://www.sphinx-doc.org/en/stable/>`__.
