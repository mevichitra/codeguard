# CG-SEC-002 tn sample 3: config file read (safe)
import json
import os

with open("config.json") as f:
    cfg = json.load(f)

DB_PASSWORD = cfg.get("db_password", "")
