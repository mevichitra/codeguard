# SPDX-License-Identifier: Apache-2.0
"""What counts as an untrusted source, a sanitizer, or a propagator for Python.

Names are canonical dotted paths after import-alias resolution
(``from flask import request as rq`` makes ``rq.args`` read as
``flask.request.args``).  Bare builtins use their plain name.
"""

from __future__ import annotations

#: Attributes of ``flask.request`` that hold client-controlled data.
FLASK_REQUEST_ATTRS = frozenset(
    {
        "args",
        "form",
        "values",
        "json",
        "data",
        "headers",
        "cookies",
        "files",
        "full_path",
        "url",
        "path",
        "query_string",
        "stream",
        "environ",
        "view_args",
    }
)

#: Methods on ``flask.request`` that return client-controlled data.
FLASK_REQUEST_METHODS = frozenset({"get_json", "get_data"})

#: Attributes of a Django / DRF / Starlette ``request`` object (a parameter or
#: ``self.request``) that hold client-controlled data.
REQUEST_OBJECT_ATTRS = frozenset(
    {
        "GET",
        "POST",
        "COOKIES",
        "META",
        "FILES",
        "body",
        "headers",
        "path",
        "path_info",
        "query_params",
        "data",
        "cookies",
        "path_params",
    }
)

#: Names conventionally bound to the incoming request.
REQUEST_NAMES = frozenset({"request", "req"})

#: Exact attribute chains that are process inputs (``kind="local"``).
LOCAL_SOURCE_CHAINS = {
    "sys.argv": "sys.argv",
    "os.environ": "os.environ",
    "sys.stdin": "sys.stdin",
}

#: Calls that return process inputs (``kind="local"``).
LOCAL_SOURCE_CALLS = {
    "input": "input()",
    "os.getenv": "os.getenv()",
    "os.environ.get": "os.environ.get()",
}

#: Decorator names (the attribute or function name) that mark a request handler
#: whose parameters come from the URL / query / body.
HANDLER_DECORATORS = frozenset(
    {"route", "get", "post", "put", "patch", "delete", "api_route", "websocket", "api_view"}
)

#: Handler parameters that are framework objects, not request values.
HANDLER_NON_DATA_PARAMS = frozenset({"self", "cls", "request", "req", "db", "session"})

#: Calls whose result is safe regardless of their argument.
SANITIZERS = frozenset(
    {
        "int",
        "float",
        "bool",
        "len",
        "shlex.quote",
        "pipes.quote",
        "html.escape",
        "markupsafe.escape",
        "flask.escape",
        "urllib.parse.quote",
        "urllib.parse.quote_plus",
        "re.escape",
        "os.path.basename",
        "werkzeug.utils.secure_filename",
        "bleach.clean",
        "django.utils.html.escape",
        "uuid.UUID",
    }
)

#: Calls whose result carries the taint of any argument.
PROPAGATORS = frozenset(
    {
        "str",
        "bytes",
        "repr",
        "format",
        "os.path.join",
        "os.path.abspath",
        "os.path.normpath",
        "os.path.expanduser",
        "os.path.realpath",
        "pathlib.Path",
        "pathlib.PurePath",
        "urllib.parse.urljoin",
        "urllib.parse.unquote",
        "urllib.parse.unquote_plus",
        "urllib.parse.urlparse",
        "base64.b64decode",
        "base64.urlsafe_b64decode",
        "json.loads",
        "json.dumps",
        "shlex.split",
        "textwrap.dedent",
        "dict",
        "list",
        "tuple",
        "set",
        "sorted",
        "reversed",
    }
)

#: Methods that return a bool / int / position even on a tainted receiver.
NON_PROPAGATING_METHODS = frozenset(
    {
        "isdigit",
        "isalnum",
        "isalpha",
        "isnumeric",
        "isdecimal",
        "isspace",
        "isidentifier",
        "startswith",
        "endswith",
        "count",
        "index",
        "find",
        "rfind",
        "__len__",
    }
)
