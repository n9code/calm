"""
Here lies the core of Calm.
"""
import json
import re
import inspect
import datetime
from collections import defaultdict

from tornado.web import Application, RequestHandler
from tornado.web import MissingArgumentError

from calm.ex import (DefinitionError, ServerError, ClientError,
                     BadRequestError, MethodNotAllowedError, NotFoundError)
from calm.codec import CalmJSONEncoder, CalmJSONDecoder, ArgumentParser
from calm.service import CalmService

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
                **default_handler_args
            }

            route_defs.append(
                (uri, MainHandler, init_params)
            )

        self._app = Application(route_defs,
                                default_handler_class=DefaultHandler,
                                default_handler_args=default_handler_args)

        return self._app

    def _add_route(self, http_method, function, *uri, **kwargs):
        """
        Maps a function to a specific URL and HTTP method.

        Arguments:
            * http_method - the HTTP method to map to
            * function - the handler function to be mapped to URL and method
            * uri - a list of URL fragments. This is used as a tuple for easy
                    implementation of the Service notion.
        """
        # TODO: split this function into smaller parts
        # Join the uri fragments
        uri = '/'.join(
            u.strip('/') for u in uri
        )
        uri = '/' + uri + '/?'

        # Convert colon-uri into a regex and then
        # get all the group names for further use
        path_params = self.URI_REGEX.findall(uri)
        for path_param in path_params:
            uri = uri.replace(
                ':{}'.format(path_param),
                r'(?P<{}>[^\/\?]*)'.format(path_param)
            )
        regex = re.compile(uri)
        path_params = list(regex.groupindex.keys())

        # Get the arguments specification of the
        # decorated function to make appropriate
        # checks
        # TODO: switch to using `inspect.signature()`
        argspec = inspect.getfullargspec(function)
        all_args = argspec.args[1:]
        has_kwargs = argspec.varkw
        default_count = len(argspec.defaults or [])
        if default_count:
            required_args = all_args[:-default_count]
            optional_args = all_args[-default_count:]
        else:
            required_args = all_args
            optional_args = []

        # Make sure no path param is defined as optional
        optional_path_params = set(
            path_params).intersection(optional_args)
        if optional_path_params:
            raise DefinitionError(
                "Path Parameters {} must not be optional in '{}'".format(
                    list(optional_args),
                    function.__name__
                )
            )

        if not has_kwargs and not set(path_params).issubset(required_args):
            missing_path_params = set(
                path_params).difference(required_args)
            raise DefinitionError(
                "Path Parameters {} must be expected by '{}'".format(
                    list(missing_path_params),
                    function.__name__
                )
            )

        all_query_params = list(
            set(all_args)
            .difference(path_params)
        )
        required_query_params = list(
            set(required_args)
            .intersection(all_query_params)
        )

        handler_def = {
            'function': function,
            'all_args': all_args,
            'path_params': path_params,
            'all_query_params': all_query_params,
            'required_query_params': required_query_params,
        }

        self._route_map[uri][http_method.lower()] = handler_def

    def _decorator(self, http_method, *uri, **kwargs):
        """
        A generic HTTP method decorator.

        This method simply stores all the mapping information needed, and
        returns the original function.
        """
        def wrapper(function):
            self._add_route(http_method, function, *uri, **kwargs)
            return function

        return wrapper

    def get(self, *uri, **kwargs):
        """Define GET handler for `uri`"""
        return self._decorator("GET", *uri, **kwargs)

    def post(self, *uri, **kwargs):
        """Define POST handler for `uri`"""
        return self._decorator("POST", *uri, **kwargs)

    def delete(self, *uri, **kwargs):
        """Define DELETE handler for `uri`"""
        return self._decorator("DELETE", *uri, **kwargs)

    def put(self, *uri, **kwargs):
        """Define PUT handler for `uri`"""
        return self._decorator("PUT", *uri, **kwargs)

    def service(self, url):
        """Returns a Service defined by the `url` prefix"""
        return CalmService(self, url)


class MainHandler(RequestHandler):
    """
    The main dispatcher request handler.

    This class extends the Tornado `RequestHandler` class, and it is mapped to
    all the defined applications handlers handlers. This class implements all
    HTTP method handlers, which dispatch the control to the appropriate user
    handlers based on their definitions and request itself.
    """
    BUILTIN_TYPES = (str, list, tuple, set, int, float, datetime.datetime)

    def __init__(self, *args, **kwargs):
        """
        Initializes the dispatcher request handler.

        Arguments:
            * get, post, put, delete - appropriate HTTP method handler for
                                       a specific URI
            * argument_parser - a `calm.ArgumentParser` subclass
            * app - the Calm application
        """
        self._get_handler = kwargs.pop('get', None)
        self._post_handler = kwargs.pop('post', None)
        self._put_handler = kwargs.pop('put', None)
        self._delete_handler = kwargs.pop('delete', None)

        self._argument_parser = kwargs.pop('argument_parser')()
        self._app = kwargs.pop('app', None)

        super(MainHandler, self).__init__(*args, **kwargs)

    def _get_query_params(self, handler_def):
        """Retreives the values for query arguments."""
        query_params = {}
        for qparam in handler_def['all_query_params']:
            try:
                query_params[qparam] = self.get_query_argument(qparam)
            except MissingArgumentError:
                if qparam not in handler_def['required_query_params']:
                    continue

                raise BadRequestError(
                    "Missing required query param '{}'".format(qparam)
                )

        return query_params

    def _cast_args(self, handler, args):
        """Converts the request arguments to appropriate types."""
        arg_types = handler.__annotations__
        for arg in args:
            arg_type = arg_types.get(arg)

            if not arg_type:
                continue

            args[arg] = self._argument_parser.parse(arg_type, args[arg])

    def _parse_and_update_body(self):
        """Parses the request body to JSON."""
        if self.request.body:
            try:
                json_body = json.loads(self.request.body.decode('utf-8'),
                                       cls=CalmJSONDecoder)
                self.request.body = json_body
            except json.JSONDecodeError:
                raise BadRequestError(
                    "Malformed request body. JSON is expected."
                )

    async def _handle_request(self, handler_def, **kwargs):
        """A generic HTTP method handler."""
        if not handler_def:
            raise MethodNotAllowedError()

        handler = handler_def['function']
        kwargs.update(self._get_query_params(handler_def))
        self._cast_args(handler, kwargs)
        self._parse_and_update_body()
        if inspect.iscoroutinefunction(handler):
            resp = await handler(self.request, **kwargs)
        else:
            # TODO: warn about blocking call
            resp = handler(self.request, **kwargs)

        self._write_response(resp)

    async def get(self, **kwargs):
        """The HTTP GET handler."""
        await self._handle_request(self._get_handler, **kwargs)

    async def post(self, **kwargs):
        """The HTTP POST handler."""
        await self._handle_request(self._post_handler, **kwargs)

    async def put(self, **kwargs):
        """The HTTP PUT handler."""
        await self._handle_request(self._put_handler, **kwargs)

    async def delete(self, **kwargs):
        """The HTTP DELETE handler."""
        await self._handle_request(self._delete_handler, **kwargs)

    def _write_response(self, response):
        """Converts various types to JSON and returns to the client"""
        if hasattr(response, '__json__'):
            result = response.__json__()
        elif isinstance(response, dict):
            result = response
        elif isinstance(response, self.BUILTIN_TYPES):
            result = {
                self._app.config['plain_result_key']: response
            }
        else:
            raise ServerError(
                "Could not serialize '{}' to JSON".format(
                    type(response).__name__
                )
            )

        self._write_dict(result)

    def _write_dict(self, response_dict):
        """Converts a `dict` object to JSON string and returns to the client"""
        result = json.dumps(response_dict, cls=CalmJSONEncoder)

        self.write(result)

    def write_error(self, status_code, exc_info=None, **kwargs):
        """The top function for writing errors"""
        if exc_info:
            exc_type, exc_inst, _ = exc_info
            if issubclass(exc_type, ClientError):
                self._write_client_error(exc_inst)
                return

        self._write_server_error()

    def _write_client_error(self, exc):
        """Formats and returns a client error to the client"""
        result = {
            self._app.config['error_key']: exc.message or str(exc)
        }

        self.set_status(exc.code)
        self.write(json.dumps(result))

    def _write_server_error(self):
        """Formats and returns a server error to the client"""
        result = {
            self._app.config['error_key']: 'Oops our bad. '
                                           'We are working to fix this!'
        }

        self.set_status(500)
        self.write(json.dumps(result))


class DefaultHandler(MainHandler):
    """
    This class extends the main dispatcher class for request handlers
    `MainHandler`:
    It implements prepare method and passed as an default_handler_class for
    Tornado Application instance

    """
    def prepare(self):
        raise NotFoundError()
