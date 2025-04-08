# coding=utf-8
"""

* project : cyberRangeHostManage
* author  : shanyongbo
* file   : host_manage_Exception.py
* corp   : NSFOCUS Corporation
* time   : 2022-03-14

"""


class BaseException(Exception):
    def __init__(self, message="未知错误", code=-1):
        self.message = message
        self.code = code

    def __str__(self):
        return f"{self.__class__.__name__}, Exception message: {self.message}, Exception_code: {self.code}"


class BusinessException(BaseException):
    """业务执行异常"""

    def __init__(self, message, code=10001):
        super().__init__(message, code)
