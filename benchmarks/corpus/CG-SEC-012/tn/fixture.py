# literal_eval and constants do not trigger.
import ast

from flask import request


def calc():
    data = ast.literal_eval(request.json["expr"])
    return eval("1 + 1"), data
