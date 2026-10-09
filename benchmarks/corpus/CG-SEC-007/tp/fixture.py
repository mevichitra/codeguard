# TLS certificate verification turned off.
import ssl

import httpx
import requests

requests.get("https://internal.example", verify=False)
client = httpx.Client(verify=False)
ctx = ssl._create_unverified_context()

context = ssl.create_default_context()
context.check_hostname = False
context.verify_mode = ssl.CERT_NONE


def fetch(session):
    return session.post("https://api.example", json={}, verify=False)
