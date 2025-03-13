import json

from rest_framework.response import Response


def ok_response(data, message=u"成功", code=0):
    """返回正常的HTTP响应结果"""
    result = {
        "code": code,
        "data": data,
        "message": message
    }
    return Response(json.dumps(result), status=200, content_type="text/json")


def error_response(except_msg=u"接口异常,请联系管理员", code=500):
    """返回异常的HTTP响应结果"""
    result = {
        "code": code,
        "data": {},
        "message": str(except_msg)
    }
    return Response(json.dumps(result), status=200, content_type="text/json")
