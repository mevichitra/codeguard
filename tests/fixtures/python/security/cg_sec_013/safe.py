# secure_filename / basename, and CLI arguments, do not trigger.
import os
import sys

from flask import request, send_from_directory
from werkzeug.utils import secure_filename


def download():
    name = secure_filename(request.args["file"])
    return open(os.path.join("/srv/files", name))


def download2():
    return send_from_directory("/srv/files", request.args["file"])


def main():
    with open(sys.argv[1]) as fh:
        print(fh.read())
