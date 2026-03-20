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

    > permaculture --help
    usage: permaculture [-h] {help,ingest,iterate,list,lookup,search,store} ...

    positional arguments:
      {help,ingest,iterate,list,lookup,search,store}
                            permaculture command
        help                show configuration help
        iterate             iterate over all scientific names
        list                list available databases
        lookup              lookup characteristics by scientific name
        search              search for the scentific name by common name
        store               store a file for a storage key

    options:
      -h, --help            show this help message and exit

Configuration
-------------

The ``permaculture`` command can be configured with options on the
command-line or the same options in an INI configuration file: either
``.permaculture`` in your current working directory or ``~/.permaculture``
in your home directory. To configure logging:

.. code-block:: text

    log-level = debug
    log-file = permaculture.log

Web Interface
-------------

A minimal web interface with a REST API is also available. Install the
API extra:

.. code-block:: text

    pip install permaculture[web]

Start the server:

.. code-block:: text

    permaculture-web
    permaculture-web --host 0.0.0.0 --port 9000

Then open http://127.0.0.1:8000 in a browser to search and browse
plants. The API is also available directly:

.. code-block:: text

    GET /permaculture/plants?q=comfrey&limit=10
    GET /permaculture/plants/symphytum%20officinale

Interactive API documentation is at ``/permaculture/docs``.

The web interface also includes an MCP server automatically
mounted at ``/permaculture/mcp/`` (SSE transport), so a single
``permaculture-web`` process serves the web UI, REST API, and
MCP server.

ChatGPT App
-----------

The MCP server can be added to ChatGPT as an App:

1. Settings > Apps > Advanced Settings
   * Enable ``Developer Mode``
2. Settings > Apps > Create app
   * Name: Permaculture
   * MCP Server URL: ``https://[server hostname]/permaculture/mcp/``

Project Information
-------------------

* `Documentation <https://cr3.github.io/permaculture/>`__
