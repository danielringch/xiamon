import yaml

class Config:
    def __init__(self, path):
        with open(path, "r") as stream:
            self.data = yaml.safe_load(stream)

    def get_value_or_default(self, default, *keys):
        data = self.data
        for key in keys:
            try:
                if key in data:
                    data = data[key]
                else:
                    return default, False
            except TypeError:
                return default, False
        return data, True
