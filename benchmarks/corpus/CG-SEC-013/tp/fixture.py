# Request data used as a file path.
import os

from flask import request, send_file


def download():
    name = request.args["file"]
    path = os.path.join("/srv/files", name)
    return send_file(path)


def view(request):
    with open("/srv/" + request.GET["doc"]) as fh:
        return fh.read()
