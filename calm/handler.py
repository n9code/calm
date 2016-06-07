"""
This module extends and defines Torndo RequestHandlers.

Classes:
    * MainHandler - this is the main RequestHandler subclass, that is mapped to
                    all URIs and serves as a dispatcher handler.
    * DefaultHandler - this class serves all the URIs that are not defined
                       within the application, returning `404` error.
"""
import json
import inspect
import datetime

from tornado.web import RequestHandler
from tornado.web import MissingArgumentError

from calm.ex import (ServerError, ClientError, BadRequestError,
                     MethodNotAllowedError, NotFoundError)
from calm.codec import CalmJSONEncoder, CalmJSONDecoder

__all__ = ['MainHandler', 'DefaultHandler']


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

    def _get_query_args(self, handler_def):
        """Retreives the values for query arguments."""
        query_args = {}
        for qarg, is_required in handler_def.query_args.items():
            try:
                query_args[qarg] = self.get_query_argument(qarg)
            except MissingArgumentError:
                if not is_required:
                    continue

                raise BadRequestError(
                    "Missing required query argument '{}'".format(qarg)
                )

        return query_args

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

        handler = handler_def.handler
        kwargs.update(self._get_query_args(handler_def))
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
    `MainHandler`.

    It implements the `_handle_request` method and raises `NotFoundError` which
    will be returned to the user as an appropriate JSON message.
    """
    def _handle_request(self, *_, **dummy):
        raise NotFoundError()
