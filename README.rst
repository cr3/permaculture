Permaculture Design Toolkit
===========================

This is an experimental toolkit to assist in permaculture design.

Usage
-----

To ``search`` for the scientific name of a plant by common name:

.. code-block:: text

    > permaculture search consoude
    symphytum officinale:
    - Comfrey
    - Consoude
    symphytum uplandicum:
    - Consoude russe
    - Rusian comfrey

To ``lookup`` the characteristics of a plant by scientific name:

.. code-block:: text

    > permaculture lookup "symphytum officinale"
    Accumulateur de Nutriments: X
    Acid: 0
    Alkaline: 0
    Author: L.
    Comestible: '*'
    ...


Configuration
-------------

The ``permaculture`` command can be configured with options on the
command-line or the same options in an INI configuration file: either
``.permaculture`` in your current working directory or ``~/.permaculture``
in your home directory. To configure logging:

.. code-block:: text

    log-level = debug
    log-file = permaculture.log

Project Information
-------------------

* `Documentation <https://cr3.github.io/permaculture/>`__
* `Contributing <https://github.com/cr3/permaculture/blob/main/.github/CONTRIBUTING.md>`__
