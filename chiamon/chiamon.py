import argparse, os, yaml, asyncio, time
import warnings
from pytz_deprecation_shim import PytzUsageWarning

from core import *
from interfaces import *
from plugins import *

__version__ = "0.5.0"

warnings.filterwarnings(
    "ignore",
    category=PytzUsageWarning
)

prefix = '[chiamon] {0}'

available_interfaces = {'stdout': Stdout, 
                        'discordbot': Discordbot}
available_plugins = {'chianode': Chianode,
                     'chiawallet': Chiawallet,
                     'flexfarmer': Flexfarmer,
                     'flexpool': Flexpool,
                     'pingdrive': Pingdrive}

async def main():
    print(f'Chiamon {__version__}')

    parser = argparse.ArgumentParser(description='Monitor for chia nodes.')
    parser.add_argument('-c', '--config', type=str, required=True, help="Path to config file.")
    parser.add_argument('-m', '--manual', type=str, required=False, nargs='+', help="Run job manually on startup.")
    args = parser.parse_args()

    with open(args.config, "r") as stream:
        config = yaml.safe_load(stream)
    
    interfaces = {}
    plugins = {}

    scheduler = Scheduler()

    for key, value in config['interfaces'].items():
        print(f'Loading interface {key}...')
        interface_config = get_config_path(key, available_interfaces, value, args.config)
        if interface_config is None:
            continue
        interface = available_interfaces[key](interface_config)
        await interface.start()
        interfaces[key] = interface

    for key, value in config['plugins'].items():
        print(f'Loading plugin {key}...')
        plugin_config = get_config_path(key, available_plugins, value, args.config)
        if plugin_config is None:
            continue
        plugin = available_plugins[key](plugin_config, scheduler, interfaces.values())
        plugins[key] = plugin

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
        time.sleep(60)
        await scheduler.run()

def get_config_path(item, available_items, config, config_root_dir):
    if item not in available_items:
        print(prefix.format(f'WARNING: {item} given in config, but not available.'))
        return None
    subconfig_path = os.path.join(os.path.dirname(config_root_dir), config)
    if not os.path.exists(subconfig_path):
        print(prefix.format(f'WARNING: no config file available for {item}.'))
        return None
    return subconfig_path

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(main())
    finally:
        loop.close()
