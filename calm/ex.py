"""
This module defines the custom exception hierarchy of Calm.

The base exception is `CalmError` from which all the other exceptions
inherit. On the next level, there come two exceptions:

    ClientError - this is the root exception for all the errors that are
                  caused by the client action. This exception (or a child)
                  should be risen when there is an error in the client's
                  request and cannot be processed further.
    ServerError - this one is the root exception for all the errors that are
                  caused by the application, specifically an incorrect usage
                  of Calm by the application.

"""


class CalmError(Exception):
    """The omnipresent exception of Calm."""
    pass


class ClientError(CalmError):
    """
    The root class for client errors.

    This class has attributes `code` and `message`. The `code` value defines
    what HTTP status code will be returned to the client when this exceptions
    (or a child) is risen. The message attribute defines the actual message
    that will be returned to the client as a response body. If there is no
    message defined for the exception, the string using which the exceptions
    is initialized while rising will be exposed to the client.
    """
    code = None
    message = None


class BadRequestError(ClientError):
    """
    The error when client made the request incorrectly.

    Examples are malformed request body, missing arguments, etc.
    """
    code = 400


class ArgumentParseError(BadRequestError):
    """Error when Calm has trouble parsing the request arguments."""
    pass


class MethodNotAllowedError(ClientError):
    """Error when the request method is not implemented for the URL."""
    code = 405
    message = "Method not allowed"


class NotFoundError(ClientError):
    """Error when the requested URL is not found."""
    code = 404
    message = "Resource not found"


class ServerError(CalmError):
    """The root class for server errors."""
    pass


class DefinitionError(ServerError):
    """Error when the application programmer uses Calm incorrectly."""
    pass
