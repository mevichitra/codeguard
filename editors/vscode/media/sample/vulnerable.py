"""A deliberately vulnerable file for trying CodeGuard. Do not deploy this."""

import hashlib
import os
import random

import requests
from flask import Flask, request

app = Flask(__name__)


@app.route("/ping")
def ping():
    host = request.args.get("host", "localhost")
    cmd = "ping -c 1 " + host
    os.system(cmd)  # untrusted input reaches the shell: hover to see the data flow
    return "ok"


def hash_password(password):
    return hashlib.md5(password.encode()).hexdigest()


def make_reset_token():
    return "".join(random.choice("abcdef0123456789") for _ in range(32))  # quick fix available


def fetch(url):
    return requests.get(url, verify=False)


def count_sources(paths, settings):
    n = 0
    for p in paths:
        if p.lower() in [".py", ".js", ".ts"]:  # quick fix: use a set
            n += 1
    for key in settings.keys():  # quick fix: drop .keys()
        n += len(key)
    return n


def add(item, bucket=[]):
    bucket.append(item)
    return bucket
