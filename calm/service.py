"""
This module defines a class that implements the notion of a Service.

When the user defines several handlers that share a common URL prefix, Calm
enables them to define a Service using that common prefix. Afterwards, all
that handlers can be defines using that prefix, without specifying the
repeating common prefix, eliminating duplication and irritating bugs.
"""


class CalmService(object):
    """
    This class implements the Service notion.

    An instance of this class is initialized when `calm.Application.service()`
    is called, with the service prefix. This class simply redefines the HTTP
    method decorators by prepending the Service prefix to the handler URL.
    """

    def __init__(self, app, url):
        """
        Initializes a Calm Service.

        Arguments:
            app - the calm application the service belongs to
            url - the service prefix
        """
        super(CalmService, self).__init__()

        self._app = app
        self._url = url

    def get(self, *url):
        """Extends the GET HTTP method decorator."""
        return self._app.get(self._url, *url)

    def post(self, *url):
        """Extends the POST HTTP method decorator."""
        return self._app.post(self._url, *url)

    def put(self, *url):
        """Extends the PUT HTTP method decorator."""
        return self._app.put(self._url, *url)

    def delete(self, *url):
        """Extends the DELETE HTTP method decorator."""
        return self._app.delete(self._url, *url)

    def custom_handler(self, *url, init_args=None):
        """Extends the custom handler addition to support services."""
        return self._app.custom_handler(self._url, *url, init_args=init_args)
