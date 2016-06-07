"""
Here lies the core of Calm.
"""
import re
import inspect
from inspect import Parameter
from collections import defaultdict

from tornado.web import Application

from calm.ex import DefinitionError
from calm.codec import ArgumentParser
from calm.service import CalmService
from calm.handler import MainHandler, DefaultHandler

__all__ = ['CalmApp']


class CalmApp(object):
    """
    This class defines the Calm Application.

    Starts using calm by initializing an instance of this class. Afterwards,
    the application is being defined by calling its instance methods,
    decorators on your user-defined handlers.

    Public Methods:
        * configure - use this method to tweak some configuration parameter
                      of a Calm Application
        * get, post, put, delete - appropriate HTTP method decorators.
                                   The user defined handlers should be
                                   decorated by these decorators specifying
                                   the URL
        * service - creates a new Service using provided URL prefix
        * make_app - compiles the Calm application and returns a Tornado
                     Application instance
    """
    URI_REGEX = re.compile(r':([^\/\?:]*)')
    config = {  # The default configuration
        'argument_parser': ArgumentParser,
        'plain_result_key': 'result',
        'error_key': 'error'
    }

    def __init__(self):
        super(CalmApp, self).__init__()

        self._app = None
        self._route_map = defaultdict(dict)

    def configure(self, **kwargs):
        """
        Configures the Calm Application.

        Use this method to customize the Calm Application to your needs.
        """
        self.config.update(kwargs)

    def make_app(self):
        """Compiles and returns a Tornado Application instance."""
        route_defs = []

        default_handler_args = {
            'argument_parser': self.config.get('argument_parser',
                                               ArgumentParser),
            'app': self
        }

        for uri, methods in self._route_map.items():
            init_params = {
                **methods,  # noqa
                **default_handler_args  # noqa
            }

            route_defs.append(
                (uri, MainHandler, init_params)
            )

        self._app = Application(route_defs,
                                default_handler_class=DefaultHandler,
                                default_handler_args=default_handler_args)

        return self._app

    def _normalize_uri(self, *uri_fragments):
        """Convert colon-uri into a regex."""
        uri = '/'.join(
            u.strip('/') for u in uri_fragments
        )
        uri = '/' + uri + '/?'

        path_params = self.URI_REGEX.findall(uri)
        for path_param in path_params:
            uri = uri.replace(
                ':{}'.format(path_param),
                r'(?P<{}>[^\/\?]*)'.format(path_param)
            )

        return uri

    def _add_route(self, http_method, function, *uri_fragments):
        """
        Maps a function to a specific URL and HTTP method.

        Arguments:
            * http_method - the HTTP method to map to
            * function - the handler function to be mapped to URL and method
            * uri - a list of URL fragments. This is used as a tuple for easy
                    implementation of the Service notion.
        """
        uri = self._normalize_uri(*uri_fragments)
        self._route_map[uri][http_method.lower()] = HandlerDef(uri, function)

    def _decorator(self, http_method, *uri, **kwargs):
        """
        A generic HTTP method decorator.

        This method simply stores all the mapping information needed, and
        returns the original function.
        """
        def wrapper(function):
            """Takes a record of the function and returns it."""
            self._add_route(http_method, function, *uri, **kwargs)
            return function

        return wrapper

    def get(self, *uri):
        """Define GET handler for `uri`"""
        return self._decorator("GET", *uri)

    def post(self, *uri):
        """Define POST handler for `uri`"""
        return self._decorator("POST", *uri)

    def delete(self, *uri):
        """Define DELETE handler for `uri`"""
        return self._decorator("DELETE", *uri)

    def put(self, *uri):
        """Define PUT handler for `uri`"""
        return self._decorator("PUT", *uri)

    def service(self, url):
        """Returns a Service defined by the `url` prefix"""
        return CalmService(self, url)


class HandlerDef(object):
    """
    Defines a request handler.

    During initialization, the instance will process and store all argument
    information.
    """
    URI_REGEX = re.compile(r':([^\/\?:]*)')

    def __init__(self, uri, handler):
        super(HandlerDef, self).__init__()

        self.uri = uri
        self.handler = handler
        self._signature = inspect.signature(handler)
        self._params = {
            k: v for k, v in list(
                self._signature.parameters.items()
            )[1:]
        }

        self.path_args = []
        self.query_args = {}

        self._extract_arguments()

    def _extract_path_args(self):
        """Extracts path arguments from the URI."""
        regex = re.compile(self.uri)
        self.path_args = list(regex.groupindex.keys())

        for path_arg in self.path_args:
            if path_arg in self._params:
                if self._params[path_arg].default is not Parameter.empty:
                    raise DefinitionError(
                        "Path argument '{}' must not be optional in '{}'"
                        .format(
                            path_arg,
                            self.handler.__name__
                        )
                    )
            else:
                raise DefinitionError(
                    "Path argument '{}' must be expected by '{}'".format(
                        path_arg,
                        self.handler.__name__
                    )
                )

    def _extract_query_arguments(self):
        """
        Extracts query arguments from handler signature

        Should be called after path arguments are extracted.
        """
        for _, param in self._params.items():
            if param.name not in self.path_args:
                self.query_args[param.name] = param.default is Parameter.empty

    def _extract_arguments(self):
        """Extracts path and query arguments."""
        self._extract_path_args()
        self._extract_query_arguments()
