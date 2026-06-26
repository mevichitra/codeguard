# CG-SEC-002 tp sample 3: hardcoded private key
# VULNERABLE
PRIVATE_KEY = """-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA0gD1nW0uDYeYqkX0jRItJ6JLz
-----END RSA PRIVATE KEY-----"""

def decrypt(data):
    from cryptography.fernet import Fernet
    return Fernet(PRIVATE_KEY).decrypt(data)
