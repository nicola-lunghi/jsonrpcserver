import json

import pytest

from jsonrpcserver import status
from jsonrpcserver.response import (
    BatchResponse,
    ErrorResponse,
    ExceptionResponse,
    InvalidParamsResponse,
    NotificationResponse,
    Response,
    SuccessResponse,
    sort_dict_response,
)


def test_response():
    Response()
    assert True


def test_response_http_status():
    response = Response(http_status=1)
    assert response.http_status == 1


def test_notification_response():
    response = NotificationResponse()
    assert str(response) == ""
    assert response.http_status == 204


def test_notification_response_str():
    assert str(NotificationResponse()) == ""


def test_batch_response():
    str(BatchResponse([SuccessResponse("foo", id=1)]))


def test_sort_dict_response_success():
    response = sort_dict_response({"id": 1, "result": 5, "jsonrpc": "2.0"})
    assert json.dumps(response) == '{"jsonrpc": "2.0", "result": 5, "id": 1}'


def test_sort_dict_response_error():
    response = sort_dict_response(
        {
            "id": 1,
            "error": {
                "data": "bar",
                "message": "foo",
                "code": status.JSONRPC_INVALID_REQUEST_CODE,
            },
            "jsonrpc": "2.0",
        }
    )
    assert (
        json.dumps(response)
        == '{"jsonrpc": "2.0", "error": {"code": -32600, "message": "foo", "data": "bar"}, "id": 1}'
    )


def test_success_response():
    response = SuccessResponse("foo", 1)
    assert response.result == "foo"
    assert str(response) == '{"jsonrpc": "2.0", "result": "foo", "id": 1}'


def test_success_response_str():
    response = SuccessResponse("foo", 1)
    assert str(response) == '{"jsonrpc": "2.0", "result": "foo", "id": 1}'


def test_success_response_null_id():
    # OK - any id is acceptable
    response = SuccessResponse("foo", None)
    assert str(response) == '{"jsonrpc": "2.0", "result": "foo", "id": null}'


def test_success_response_null_result():
    # Perfectly fine.
    response = SuccessResponse(None, 1)
    assert str(response) == '{"jsonrpc": "2.0", "result": null, "id": 1}'


def test_error_response():
    response = ErrorResponse(-1, "foo", id=1, debug=True)
    assert response.code == -1
    assert response.message == "foo"
    assert (
        str(response)
        == '{"jsonrpc": "2.0", "error": {"code": -1, "message": "foo"}, "id": 1}'
    )


def test_error_response_no_id():
    # Responding with an error to a Notification - this is OK; we do respond to
    # notifications under certain circumstances, such as "invalid json" and "invalid
    # json-rpc".
    assert (
        str(ErrorResponse(-1, "foo", debug=True))
        == '{"jsonrpc": "2.0", "error": {"code": -1, "message": "foo"}}'
    )


def test_error_response_data_with_debug_disabled():
    # The data is not included, because debug=True is not passed
    assert (
        str(ErrorResponse(-1, "foo", data="bar", debug=False))
        == '{"jsonrpc": "2.0", "error": {"code": -1, "message": "foo"}}'
    )


def test_error_response_data_with_debug_enabled():
    assert (
        str(ErrorResponse(-1, "foo", data="bar", debug=True))
        == '{"jsonrpc": "2.0", "error": {"code": -1, "message": "foo", "data": "bar"}}'
    )


def test_exception_response():
    assert (
        str(ExceptionResponse(ValueError("foo"), debug=True))
        == '{"jsonrpc": "2.0", "error": {"code": -32000, "message": "Server error", "data": "ValueError: foo"}}'
    )


def test_exception_response_with_id():
    assert (
        str(ExceptionResponse(ValueError("foo"), id=1, debug=True))
        == '{"jsonrpc": "2.0", "error": {"code": -32000, "message": "Server error", "data": "ValueError: foo"}, "id": 1}'
    )


def test_exception_response_debug_enabled():
    response = ExceptionResponse(ValueError("There was an error"), debug=True)
    assert (
        str(response)
        == '{"jsonrpc": "2.0", "error": {"code": -32000, "message": "Server error", "data": "ValueError: There was an error"}}'
    )


def test_error_response_http_status():
    response = ErrorResponse(-1, "foo", http_status=status.HTTP_BAD_REQUEST, debug=False)
    assert response.http_status == status.HTTP_BAD_REQUEST
