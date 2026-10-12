"""Tokens and passwords from the random module."""

import random
import string
import secrets

ALPHABET = string.ascii_letters + string.digits


def make_password(length: int = 16) -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(length))


session_token = secrets.randbits(128)
otp = random.randint(100000, 999999)
