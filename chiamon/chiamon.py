import argparse, os, yaml, asyncio, time
import warnings
from pytz_deprecation_shim import PytzUsageWarning

from src.core import Scheduler
from src.interfaces import *
from src.plugins import *

__version__ = "0.9.0"

warnings.filterwarnings(
    "ignore",
    category=PytzUsageWarning
)

prefix = '[chiamon] {0}'

available_interfaces = {'discordbot': Discordbot,
                        'logfile': Logfile,
                        'stdout': Stdout}
available_plugins = {'chiafarmer': Chiafarmer,
                     'chianode': Chianode,
                     'chiawallet': Chiawallet,
                     'flexfarmer': Flexfarmer,
                     'flexpool': Flexpool,
                     'pingdrive': Pingdrive,
                     'smartctl': Smartctl}

async def main():
    print(f'Chiamon {__version__}')

    parser = argparse.ArgumentParser(description='Monitor for chia nodes.')
    parser.add_argument('-c', '--config', type=str, required=True, help="Path to config file.")
    parser.add_argument('-m', '--manual', type=str, required=False, nargs='+', help="Run job manually on startup.")
    parser.add_argument('-i', '--interface', type=str, required=False, nargs='+', help="Override selected interfaces.")
    args = parser.parse_args()

    with open(args.config, "r") as stream:
        config = yaml.safe_load(stream)
    
    interfaces = {}
    plugins = {}

    scheduler = Scheduler()

    for key, value in config['interfaces'].items():
        if args.interface and key not in args.interface:
            print(f'Interface {key} ignored.')
            continue
        print(f'Loading interface {key}...')
        interface_config = get_config_path(key, available_interfaces, value, args.config)
        if interface_config is None:
            continue
        interface = available_interfaces[key](interface_config, scheduler)
        await interface.start()
        interfaces[key] = interface

    for key, value in config['plugins'].items():
        paths = [value] if isinstance(value, str) else value
        for path in paths:
            print(f'Loading plugin {key}...')
            plugin_config = get_config_path(key, available_plugins, path, args.config)
            if plugin_config is None:
                continue
            plugin = available_plugins[key](plugin_config, scheduler, interfaces.values())
            plugins[plugin.name] = plugin

    await scheduler.start(interfaces.values())

    manual_tasks = []
    if args.manual:
        for manual_job in args.manual:
            print(prefix.format(f'Manual run of job {manual_job}.'))
            manual_tasks.append(scheduler.manual(manual_job))
    await asyncio.gather(*manual_tasks)

    print(prefix.format('Startup complete.'))

    await schedule_plugins(scheduler)

async def schedule_plugins(scheduler):
    while True:
        time.sleep(20)
        await scheduler.run()

def get_config_path(item, available_items, config, config_root_dir):
    if item not in available_items:
        print(prefix.format(f'WARNING: {item} given in config, but not available.'))
        return None
    subconfig_path = os.path.join(os.path.dirname(config_root_dir), config)
    if not os.path.exists(subconfig_path):
        print(prefix.format(f'WARNING: config file for plugin {item} not found: {subconfig_path}.'))
        return None
    return subconfig_path

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(main())
    finally:
        loop.close()
