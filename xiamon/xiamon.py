import argparse, sys, os, shutil, yaml, asyncio, time
import warnings
from pytz_deprecation_shim import PytzUsageWarning

from src.core import Scheduler
from src.interfaces import *
from src.plugins import *

__version__ = "1.1.0"

warnings.filterwarnings(
    "ignore",
    category=PytzUsageWarning
)

prefix = '[xiamon] {0}'

available_interfaces = {'discordbot': Discordbot,
                        'logfile': Logfile,
                        'stdout': Stdout}
available_plugins = {'chiaharvester': Chiaharvester,
                     'chiafarmer': Chiafarmer,
                     'chianode': Chianode,
                     'chiawallet': Chiawallet,
                     'diskfree': Diskfree,
                     'eccram': Eccram,
                     'flexfarmer': Flexfarmer,
                     'flexpool': Flexpool,
                     'messagerelay': Messagerelay,
                     'pingdrive': Pingdrive,
                     'serviceping': Serviceping,
                     'siahost' : Siahost,
                     'smartctl': Smartctl,
                     'storjnode': Storjnode,
                     'sysmonitor': Sysmonitor}

async def main():
    print(f'Xiamon {__version__}')

    parser = argparse.ArgumentParser(description='Monitor for chia nodes.')
    parser.add_argument('-c', '--config', type=str, required=True, help="Path to config file.")
    parser.add_argument('-m', '--manual', type=str, required=False, nargs='+', help="Run job manually on startup.")
    parser.add_argument('-i', '--interface', type=str, required=False, nargs='+', help="Override selected interfaces.")
    args = parser.parse_args()

    config_file = os.path.join(args.config, 'xiamon.yaml')
    copy_configuration_templates(config_file, args.config)
    with open(config_file, "r") as stream:
        config = yaml.safe_load(stream)
    
    interfaces = []
    plugins = {}

    scheduler = Scheduler()

    for key, value in config['interfaces'].items():
        if args.interface and key not in args.interface:
            print(f'Interface {key} ignored.')
            continue
        paths = [value] if isinstance(value, str) else value
        for path in paths:
            check_item(key, available_interfaces)
            interface = available_interfaces[key](get_config_path(path, args.config), scheduler)
            await interface.start()
            interfaces.append(interface)

    for key, value in config['plugins'].items():
        paths = [value] if isinstance(value, str) else value
        for path in paths:
            check_item(key, available_plugins)
            plugin = available_plugins[key](get_config_path(path, args.config), scheduler, interfaces)
            plugins[plugin.name] = plugin

    await scheduler.start(interfaces)

    if args.manual:
        for manual_job in args.manual:
            print(prefix.format(f'Manual run of job {manual_job}.'))
            await scheduler.manual(manual_job)

    print(prefix.format('Startup complete.'))

    await schedule_plugins(scheduler)

async def schedule_plugins(scheduler):
    while True:
        sleep_time = await scheduler.run()
        time.sleep(sleep_time)

def check_item(item, available_items):
    if item not in available_items:
        sys.exit(prefix.format(f'Error: Plugin or interface "{item}" is unknown.'))

def get_config_path(config, config_root_dir):
    subconfig_path = os.path.join(config_root_dir, config)
    if not os.path.exists(subconfig_path):
        sys.exit(prefix.format(f'Error: config file not found: {subconfig_path} .'))
    return subconfig_path

def copy_configuration_templates(config_file, config_path):
    if os.path.exists(config_file):
        return
    if not os.path.exists(config_path):
        sys.exit(f'Error: the configuration path {config_path} does not exist.')
    if not os.path.exists(os.path.join('config', 'xiamon.yaml')) \
            or not os.path.exists('xiamon/xiamon.py'):
        sys.exit('Error: can not copy configuration file templates, can not find templates.')
    print('Configuration file not found. Will copy the template configuration files.')
    for item in os.listdir('config'):
        item_path = os.path.join('config', item)
        if os.path.isfile(item_path):
            shutil.copy2(item_path, config_path)
        else:
            shutil.copytree(item_path, os.path.join(config_path, item))
    print('Configuration files copied.')
    sys.exit()

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(main())
    finally:
        loop.close()
