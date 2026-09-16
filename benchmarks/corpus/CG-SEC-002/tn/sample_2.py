# CG-SEC-002 tn sample 2: secrets module (safe)
import secrets

def generate_token():
    return secrets.token_hex(32)

config = {
    "host": "localhost",
    "password": secrets.token_urlsafe(16),
    "port": 5432,
}
