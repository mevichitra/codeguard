def show(config, settings):
    for key in config.keys():
        print(key)
    if "debug" in settings.options.keys():
        print("debug")
    return [k for k in config.keys() if k]
