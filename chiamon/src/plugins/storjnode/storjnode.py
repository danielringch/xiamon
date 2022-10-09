from typing import overload
from ...core import Plugin, Alert, Storjapi, Storjnodedata, Config, Conversions

class Storjnode(Plugin):
    def __init__(self, config, scheduler, outputs):
        config_data = Config(config)
        name, _ = config_data.get_value_or_default('storjnode', 'name')
        super(Storjnode, self).__init__(name, outputs)
        self.print(f'Plugin storjnode; name: {name}')

        mute_interval, _ = config_data.get_value_or_default(24, 'alert_mute_interval')

        host, _ = config_data.get_value_or_default('127.0.0.1:14002','host')
        self.__api = Storjapi(host)

        self.__request_alerts = {
            'sno' : Alert(super(Storjnode, self), mute_interval)
        }
        self.__outdated_alert = Alert(super(Storjnode, self), mute_interval)
        self.__offline_alert = Alert(super(Storjnode, self), mute_interval)
        self.__offline_alert = Alert(super(Storjnode, self), mute_interval)
        self.__disqualified_alert = Alert(super(Storjnode, self), mute_interval)
        self.__suspended_alert = Alert(super(Storjnode, self), mute_interval)
        self.__overused_alert = Alert(super(Storjnode, self), mute_interval)

        scheduler.add_job(f'{name}-check' ,self.check, config_data.get_value_or_default('0 * * * *', 'check_interval')[0])
        scheduler.add_job(f'{name}-summary', self.summary, config_data.get_value_or_default('0 0 * * *', 'summary_interval')[0])

    async def check(self):
        json = await self.__request('sno')
        if json is not None:
            data = Storjnodedata(json)
            if not data.uptodate:
                self.__outdated_alert.send('Node version is outdated')

            if not data.connected or data.satellites == 0:
                self.__offline_alert.send('Node is offline.')
            else:
                self.__offline_alert.reset(f'Node is online again, {data.satellites} satellites.')

            if data.disqualified > 0:
                self.__disqualified_alert.send(f'Node is disqualified for {data.disqualified} satellites.')
            else:
                self.__disqualified_alert.reset('Node is no longer disqualified for any satellite.')

            if data.suspended > 0:
                self.__suspended_alert.send(f'Node is suspended for {data.disqualified} satellites.')
            else:
                self.__suspended_alert.reset('Node is no longer suspended for any satellite.')

            if data.overused_space > 0:
                self.__overused_alert.send(f'Node overuses {data.overused_space} bytes storage.')
            else:
                self.__overused_alert.reset('Node does no longer overuse storage.')

    async def summary(self):
        json = await self.__request('sno')
        if json is not None:
            data = Storjnodedata(json)
            self.__print_traffic(data, Plugin.Channel.info)
            self.__print_usage(data, Plugin.Channel.info)
    
    def __print_traffic(self, data, channel):
        traffic = Conversions.byte_to_auto(data.traffic, binary=False)
        self.send(channel, f'Traffic: {traffic[0]:.2f} {traffic[1]}')

    def __print_usage(self, data, channel):
        total_space = data.total_space
        used_space = data.used_space
        trash_space = data.trash_space

        used_percent = used_space / total_space * 100.0
        trash_percent = trash_space / (used_space + trash_space) * 100.0

        used_space = Conversions.byte_to_auto(used_space, binary=False)
        trash_space = Conversions.byte_to_auto(trash_space, binary=False)

        self.send(channel, f'Memory usage: {used_space[0]:.2f} {used_space[1]} ({used_percent:.1f} %)')
        self.send(channel, f'Trash: {trash_space[0]:.2f} {trash_space[1]} ({trash_percent:.2f} %)')

    async def __request(self, cmd):
        alert = self.__request_alerts[cmd]
        async with self.__api.create_session() as session:
            try:
                json = await self.__api.get(session, cmd)
                alert.reset(f'Request "{cmd}" is successful again.')
                return json
            except Exception as e:
                alert.send(f'Request "{cmd}" failed.')
                return None