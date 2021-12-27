import yaml

class Stdout:

    __prefix = 'stdout'

    def __init__(self, config):
        with open(config, "r") as stream:
            config_data = yaml.safe_load(stream)
            self.__mute_info = config_data['mute_info']
            self.__mute_alert = config_data['mute_alert']

    async def start(self):
        print('[stdout] Stdout ready.')

    async def send_message(self, prefix, message, is_alert=False):
        if is_alert:
            if self.__mute_alert:
                return
            self.print(f'[ALERT] [stdout] [{prefix}]', message)
        else:
            if self.__mute_info:
                return
            self.print(f'[stdout] [{prefix}]', message)
        
    def print(self, prefix, message):
        lines = message.splitlines()
        print(prefix)
        for line in lines:
            print(f'    {line}')



