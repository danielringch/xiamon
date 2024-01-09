import aiohttp, asyncio
from ...core import Plugin, Conversions, CsvExporter, Tablerenderer
from .opendtudb import Opendtudb

class Opendtu(Plugin):
    def __init__(self, config, scheduler, outputs):
        super(Opendtu, self).__init__(config, outputs)

        self.__scheduler = scheduler
        self.__check_job = f'{self.name}-check'
        self.__summary_job = f'{self.name}-summary'

        self.__host = self.config.get('192.168.4.1:80', 'host')
        self.__serial = self.config.get(None, 'serial')

        self.__db = Opendtudb(self.config.data['database'])
        self.__check_csv = CsvExporter(self.config.get(None, 'verbose_csv_export'))
        self.__summary_csv = CsvExporter(self.config.get(None, 'summary_csv_export'))

        scheduler.add_job(self.__check_job ,self.check, self.config.get('0 * * * *', 'check_interval'))
        scheduler.add_job(self.__summary_job, self.summary, self.config.get('0 0 * * *', 'summary_interval'))

    async def check(self):
        async with aiohttp.ClientSession() as session:
            retries = 3
            while True:
                try:
                    if retries == 0:
                        self.msg.debug(f'Failed to read live data from {self.__host}, no retry.')
                        return
                    retries -= 1
                    async with session.get(f'http://{self.__host}/api/livedata/status') as response:
                        json = await response.json()
                        status = response.status
                    if (status >= 200 and status <= 299):
                        total_energy, day_energy = self.__get_energy(json)
                        break
                    else:
                        self.msg.debug(f'Command api/livedata/status failed with code {status}, {retries} retries left')
                except aiohttp.ClientConnectionError as e:
                    self.msg.debug(f'Command api/livedata/status failed: {str(e)}, {retries} retries left')
                await asyncio.sleep(10.0)
            
        last_total_energy = self.__db.get_latest()
        if last_total_energy is None:
            self.msg.debug('No power history data available, skipping outputs.')
            self.__db.add(total_energy)
            return
            
        energy_delta = total_energy - last_total_energy

        if energy_delta <= 0:
            self.msg.debug('No change since last update, inverter seems to be offline')
            return

        self.__db.add(total_energy)
            
        self.msg.debug(f'{energy_delta} Wh since last check; {day_energy} Wh today, {total_energy} Wh total.')
        if self.__check_csv is not None:
            self.__check_csv.add_line({
                'Delta (Wh)': energy_delta,
                'Today (Wh)': day_energy,
                'Total (Wh)': total_energy
            })

    async def summary(self):
        history = self.__db.get_since(self.__scheduler.get_last_execution(self.__summary_job))

        if history is None:
            self.msg.info(f'No data available, skipping summary.')
            return
        
        min_energy = history[0][1]
        max_energy = history[-1][1]
        fed_in_ernergy = max_energy - min_energy
        self.msg.info(f'Fed-in energy: {fed_in_ernergy} Wh.\nTotal energy: {(max_energy / 1000.0):.1f} kWh')
        if self.__summary_csv is not None:
            self.__summary_csv.add_line({
                'Delta (Wh)': fed_in_ernergy,
                'Total (Wh)': max_energy
            })
        
        table = Tablerenderer(['Timestamp', 'Delta', 'Sum'])
        table_data = table.data
        last_total = min_energy
        for timestamp, total in history:
            table_data['Timestamp'].append(timestamp)
            table_data['Delta'].append(total - last_total)
            table_data['Sum'].append(total - min_energy)
            last_total = total
        self.msg.verbose(table.render())

    def __get_energy(self, json):
        if self.__serial is None:
            total_energy = round(Conversions.reverse_autorange( \
                json["total"]["YieldTotal"]["v"],
                json["total"]["YieldTotal"]["u"],
                "Wh"))
            day_energy = round(Conversions.reverse_autorange( \
                json["total"]["YieldDay"]["v"],
                json["total"]["YieldDay"]["u"],
                "Wh"))
        else:
            total_energy = 0
            day_energy = 0
            for inverter in json["inverters"]:
                if inverter["serial"] != self.__serial:
                    continue
                for phase in inverter["AC"].values():
                    total_energy += round(Conversions.reverse_autorange( \
                        phase["YieldTotal"]["v"],
                        phase["YieldTotal"]["u"],
                        "Wh"))
                    day_energy += round(Conversions.reverse_autorange( \
                        phase["YieldDay"]["v"],
                        phase["YieldDay"]["u"],
                        "Wh"))
        return total_energy, day_energy


            
