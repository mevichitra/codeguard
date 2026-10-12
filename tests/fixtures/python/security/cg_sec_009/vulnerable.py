"""Tokens and passwords from the random module."""

import random
import string

ALPHABET = string.ascii_letters + string.digits


def make_password(length: int = 16) -> str:
    return "".join(random.choice(ALPHABET) for _ in range(length))


session_token = random.getrandbits(128)
otp = random.randint(100000, 999999)
