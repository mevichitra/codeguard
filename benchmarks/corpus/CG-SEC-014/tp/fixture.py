# Request data used as a redirect target.
from flask import redirect, request


def login_done():
    target = request.args.get("next")
    return redirect(target)
