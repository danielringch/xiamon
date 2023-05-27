import re, os
from ...core import Plugin

class Eccram(Plugin):
    CONTROLLER_PATH = '/sys/devices/system/edac/mc'

    def __init__(self, config, scheduler, outputs):
        super(Eccram, self).__init__(config, outputs)

        self.__mc_regex = re.compile(r'^mc\d+$')
        self.__ce = 0
        self.__ue = 0

        self.__check_job = f'{self.name}-check'

        scheduler.add_job(self.__check_job ,self.check, self.config.get('*/5 * * * *', 'interval'))

    async def check(self):
        with self.message_aggregator():
            if not os.path.exists(self.CONTROLLER_PATH):
                self.msg.error(f'System does not have ECC RAM support.')
                return
            
            total_ce = 0
            total_ue = 0
        
            for controller in self.__get_memory_controllers():
                ce, ue = self.__get_errors(controller)
                total_ce += ce
                total_ue += ue
                self.msg.debug(f'{controller}: {ce} correctable errors, {ue} uncorrectable errors')

            if total_ce > self.__ce:
                self.msg.alert(f'{total_ce - self.__ce} new correctable errors detected.')
            if total_ue > self.__ue:
                self.msg.alert(f'{total_ue - self.__ue} new uncorrectable errors detected.')

            self.__ce = total_ce
            self.__ue = total_ue

    def __get_memory_controllers(self):
        return [
            os.path.join(self.CONTROLLER_PATH, f)
            for f in os.listdir(self.CONTROLLER_PATH)
            if self.__mc_regex.match(f)
        ]

    @staticmethod
    def __get_errors(controller):
        with open(os.path.join(controller, 'ce_count'), 'r') as f_ce, \
            open(os.path.join(controller, 'ue_count'), 'r') as f_ue:
            return int(f_ce.read()), int(f_ue.read())
