# Request data reaches the shell.
import os
import subprocess

from flask import request


def ping():
    host = request.form["host"]
    cmd = "ping -c 1 " + host
    os.system(cmd)


def archive():
    name = request.args.get("name")
    subprocess.run(f"tar czf /tmp/{name}.tgz data", shell=True)
