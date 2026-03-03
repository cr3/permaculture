Natural Capital
===============

The `Natural Capital`_ Plant Database  is a repository of temperate
climate plant information for ecological design. It has a subscription
model that gives programmatic access to the database. After you register,
add your credentials to the ``.permaculture`` configuration file in your
home directory:

.. code-block:: text

    nc-username: <my username>
    nc-password: <my password>

Where ``<my username>``  and ``<my password>`` should be replaced with
your actual username and password.

Alternatively, you can provide the password via a file, which is useful
for `Docker secrets`_:

.. code-block:: text

    nc-password-file: /run/secrets/nc_password

.. _Natural Capital: https://permacultureplantdata.com/
.. _Docker secrets: https://docs.docker.com/engine/swarm/secrets/
