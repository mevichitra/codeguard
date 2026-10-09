# Checksums, cache keys, opted-out calls, and strong hashes do not trigger.
import hashlib


def cache_key(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()


def file_checksum(data: bytes) -> str:
    return hashlib.sha1(data).hexdigest()


def legacy_password_lookup(password: str) -> str:
    return hashlib.md5(password.encode(), usedforsecurity=False).hexdigest()


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
