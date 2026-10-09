def show(config, settings):
    for key in config:
        print(key)
    if "debug" in settings.options:
        print("debug")
    return [k for k in config if k]
