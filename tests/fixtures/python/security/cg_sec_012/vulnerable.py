# Request data is evaluated as code.
from flask import request


def calc():
    expr = request.json["expr"]
    return eval(expr)
