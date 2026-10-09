import logging


def load(path):
    try:
        return open(path).read()
    except FileNotFoundError:
        pass
    except Exception:
        logging.exception("could not read %s", path)
        raise
