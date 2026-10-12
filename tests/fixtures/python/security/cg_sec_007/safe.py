# Verification on, or a custom CA bundle.
import ssl

import requests

requests.get("https://internal.example", verify="/etc/ssl/internal-ca.pem")
requests.get("https://example.com")
context = ssl.create_default_context(cafile="ca.pem")
context.verify_mode = ssl.CERT_REQUIRED
options = {"verify": False}  # a plain dict, not a request
