# Non-security randomness (simulation, shuffling, jitter) does not trigger.
import random
import secrets

dice = random.randint(1, 6)
jitter = random.uniform(0, 0.5)
deck = list(range(52))
random.shuffle(deck)
token = secrets.token_urlsafe(32)
