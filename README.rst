Permaculture Design Toolkit
===========================

This is an experimental toolkit to assist in permaculture design.

Usage
-----

To ``search`` for the scientific name of a plant by common name:

.. code-block:: text

    > permaculture search consoude
    - symphytum officinale:
      - comfrey
      - consoude
    - symphytum x uplandicum:
      - consoude russe
      - rusian comfrey

To ``lookup`` the characteristics of a plant by scientific name:

.. code-block:: text

    > permaculture lookup "symphytum officinale"
    - animal damage: deer, gophers
      bloom period:
        max: summer
        min: spring
      chemical:
        allantoin: 12
        aluminum: 5
        ascorbic-acid: 112
        ash: 0
        asparagine: 2
    ...

To show the list of commands:

.. code-block:: text

    > poetry run permaculture --help
    usage: permaculture [-h] {companions,help,iterate,list,lookup,search,store} ...

    positional arguments:
      {companions,help,iterate,list,lookup,search,store}
                            permaculture command
        companions          plant companions list
        help                show configuration help
        iterate             iterate over all scientific names
        list                list available databases
        lookup              lookup characteristics by scientific name
        search              search for the scentific name by common name
        store               store a file for a storage key

    options:
      -h, --help            show this help message and exit

Advanced Usage
--------------

Output a CSV file of all plants that have companions:

.. code-block:: text

    > permaculture --serializer application/json \
      | jq -r 'keys[]' \
      | tr '\n' '\0' \
      | xargs -0 permaculture --serializer=text/csv lookup --exclude=common \
      | tee companions.csv


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
