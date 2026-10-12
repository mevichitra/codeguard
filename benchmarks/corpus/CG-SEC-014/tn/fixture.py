# Constant and validated redirects do not trigger.
from flask import redirect, request, url_for


def login_done():
    if request.args.get("next") == "home":
        return redirect(url_for("home"))
    return redirect("/")
