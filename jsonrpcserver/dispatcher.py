"""dispatcher.py"""

import json
import logging
import pkgutil
from funcsigs import signature

import jsonschema

from .rpc import rpc_success_response, sort_response
from .exceptions import JsonRpcServerError, ParseError, \
    InvalidRequest, MethodNotFound, InvalidParams, ServerError
from .status import HTTP_STATUS_CODES


logger = logging.getLogger(__name__)
request_log = logging.getLogger(__name__+'.request')
response_log = logging.getLogger(__name__+'.response')

json_validator = jsonschema.Draft4Validator(json.loads(pkgutil.get_data(
    __name__, 'request-schema.json').decode('utf-8')))


def _convert_params_to_args_and_kwargs(params):
    """Takes the 'params' part from the JSON-RPC request and converts it into
    positional or keyword arguments to be passed through to the handling method.

    There are four possibilities for 'params' in JSON-RPC:
        - No params at all (either 'params' is not present or the value is
          ``null``).
        - A single value eg. "params": 5 (or "5", or true etc), taken as one
          positional argument.
        - A JSON array, eg. "params": ["foo", "bar"], taken as positional
          arguments.
        - A JSON object, eg. "params: {"foo": "bar"}, taken as keyword
          arguments.

    .. versionchanged:: 1.0.12
        No longer allows both args and kwargs, as per spec.

    :param params: Arguments for the JSON-RPC method.
    """
    args = kwargs = None
    # Params is a dict? ie. "params": {"foo": "bar"}
    if isinstance(params, dict):
        kwargs = params
    # Params is a list? ie. "params": ["foo", "bar"]
    elif isinstance(params, list):
        args = params
    return (args, kwargs)


def _call(func, *args, **kwargs):
    """Call the requested method, first checking the arguments match the
    function signature."""
    try:
        params = signature(func).bind(*args, **kwargs)
    except TypeError as e:
        raise InvalidParams(str(e))
    else:
        return func(*params.args, **params.kwargs)


class Dispatcher(object):
    """Holds a list of the rpc methods, and dispatches to them."""

    def __init__(self, debug=False):
        """
        :param debug: Debug mode - includes the 'data' property in error
            responses which contain (potentially sensitive) debugging info.
            Default is False.
        """
        self._rpc_methods = {}
        self.validate_requests = True
        self.debug = debug

    def register_method(self, func, name=None):
        """Add an RPC method to the list."""
        if name is None:
            name = func.__name__
        self._rpc_methods[name] = func
        return func

    def method(self, name):
        """Add an RPC method to the list. Can be used as a decorator."""
        def decorator(f): #pylint:disable=missing-docstring
            return self.register_method(f, name)
        return decorator

    def dispatch(self, request):
        """Dispatch requests to the RPC methods.

        .. versionchanged:: 1.0.12
            Sending "'id': null" will be treated as if no response is required.
        .. versionchanged:: 2.0.0
            Removed all flask code.
            No longer accepts a "handler".

        :param request: JSON-RPC request in dict format.
        :return: Tuple containing the JSON-RPC response and an HTTP status code,
            which can be used to respond to a client.
        """
        request_log.info(json.dumps(request))

        try:
            # Validate
            if self.validate_requests:
                try:
                    json_validator.validate(request)
                except jsonschema.ValidationError as e:
                    raise InvalidRequest(e.message)

            request_method = request['method']

            # Get the positional and keyword arguments from request['params']
            (positional_args, keyword_args) = \
                _convert_params_to_args_and_kwargs(request.get('params'))

            # Get the method if available
            try:
                method = self._rpc_methods[request_method]
            except KeyError:
                raise MethodNotFound(request_method)

            # Call the method, first checking the arguments match the method
            # definition. It's no good simply calling the method and catching
            # the exception, because the caught exception may have been raised
            # from inside the method.
            result = None

            if not positional_args and not keyword_args:
                result = _call(method)

            if positional_args and not keyword_args:
                result = _call(method, *positional_args)

            if not positional_args and keyword_args:
                result = _call(method, **keyword_args)

            # if positional_args and keyword_args: # Should never happen.

            # Return a response
            request_id = request.get('id')
            if request_id is not None:
                # A response was requested
                response, status = (rpc_success_response(
                    request_id, result), 200)
            else:
                # Notification - return nothing.
                response, status = (None, 204)

        # Catch JsonRpcServerErrors raised (invalid request etc)
        except JsonRpcServerError as e:
            e.request_id = request.get('id')
            response, status = (json.loads(str(e)), e.http_status_code)
            if not self.debug:
                response['error'].pop('data')

        # Catch all other exceptions
        except Exception as e: #pylint:disable=broad-except
            # Log the exception
            logger.exception(e)
            response, status = (json.loads(str(ServerError(
                'See server logs'))), 500)
            if not self.debug:
                response['error'].pop('data')

        response_log.info(str(sort_response(response)), extra={
            'http_code': status,
            'http_reason': HTTP_STATUS_CODES[status]
        })

        return (response, status)

    def dispatch_str(self, request):
        """Wrapper for dispatch, which takes a string instead of a dict.

        :param request: JSON-RPC request string.
        """
        try:
            request = json.loads(request)
        except ValueError:
            return (json.loads(str(ParseError())), 400)
        return self.dispatch(request)
