# CG-SEC-002 tp sample 1: hardcoded API secret in variable
# VULNERABLE
API_SECRET = "sk-live-abc123def456ghi789jkl"

def get_api_key():
    return API_SECRET
