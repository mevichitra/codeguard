# CG-SEC-002 tn sample 1: environment variable (safe)
import os

API_SECRET = os.environ.get("API_SECRET")

def get_api_key():
    return API_SECRET
