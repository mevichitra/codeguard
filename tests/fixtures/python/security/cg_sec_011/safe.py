# Argument lists, quoting, and constant commands do not trigger.
import os
import shlex
import subprocess

from flask import request


def ping():
    host = request.form["host"]
    subprocess.run(["ping", "-c", "1", host])
    os.system("ping -c 1 " + shlex.quote(host))
    os.system("uptime")
