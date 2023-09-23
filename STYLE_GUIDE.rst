Style Guide
===========

This style guide extends `PEP 8`_ with recommendations that should be
followed in this project.

.. _`PEP 8`: http://www.python.org/peps/pep-0008.html

Logging
-------

Use the appropriate log level based on these meanings:

-   ``DEBUG``: troubleshooting - not for testing.
-   ``INFO``: normal operation - state changes.
-   ``WARNING``: might be a problem - inform user.
-   ``ERROR``: definitely a problem - inform developer.
-   ``FATAL/CRITICAL``: too similar to ``ERROR`` - just throw an exception.

Log message with a format string to avoid interpolating variables when
the log level is not applicable:

    .. code-block:: python

        logging.info(
            "Starting %(service)s on port %(port)s",
            {"service": service, "port": port},
        )

Testing
-------

-   `Test the interface, not the implementation.
    <https://www.youtube.com/watch?v=Xu5EhKVZdV8&t=18m2s>`__
-   `Test the messages, not the state.
    <https://www.youtube.com/watch?v=t430e6M5YAo&t=11m30s>`__
-   `Separate dependency tree from runtime tree.
    <https://www.youtube.com/watch?v=t430e6M5YAo&t=22m12s>`__
-   `Only mock types that you own.
    <https://www.youtube.com/watch?v=R9FOchgTtLM&t=25m29s>`__
-   `Unit test behavior, not methods.
    <https://www.goodreads.com/book/show/4268826-growing-object-oriented-software-guided-by-tests>`__
-   `We can write the test, but can we live with it?
    <https://www.goodreads.com/book/show/44919.Working_Effectively_with_Legacy_Code>`__
