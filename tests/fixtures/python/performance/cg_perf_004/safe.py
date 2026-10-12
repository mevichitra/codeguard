def show(config):
    names = list(config.keys())
    for key in config:
        print(key)
    for key in load().keys():
        print(key)
    return names
