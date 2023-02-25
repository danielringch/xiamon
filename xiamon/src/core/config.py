import yaml

class Config:
    def __init__(self, data):
        if isinstance(data, str):
            with open(data, "r") as stream:
                self.data = yaml.safe_load(stream)
        else:
            assert(isinstance(data, dict))
            self.data = data


    def get(self, default, *keys):
        data = self.data
        for key in keys:
            try:
                if key in data:
                    data = data[key]
                else:
                    return default
            except TypeError:
                return default
        return data

    def subconfig(self, *keys):
        data = self.data
        for key in keys:
            try:
                if key in data:
                    data = data[key]
                else:
                    return None
            except TypeError:
                return None
        return Config(data)
