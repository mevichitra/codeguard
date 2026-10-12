# MD5 / SHA-1 protecting passwords and tokens.
import hashlib
from hashlib import sha1


def hash_password(password: str) -> str:
    return hashlib.md5(password.encode()).hexdigest()


def make_reset_token(user_id: int) -> str:
    return sha1(str(user_id).encode()).hexdigest()


api_signature = hashlib.new("MD5", b"payload").hexdigest()
