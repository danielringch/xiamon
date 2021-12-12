import argparse, os, yaml, asyncio, time
import warnings
from pytz_deprecation_shim import PytzUsageWarning

from core import *
from interfaces import *
from plugins import *

__version__ = "0.2.0"

warnings.filterwarnings(
    "ignore",
    category=PytzUsageWarning
)

prefix = '[chiamon] {0}'

available_plugins = {'flexfarmer': Flexfarmer, 'pingdrive': Pingdrive}

async def main():
    print(f'Chiamon {__version__}')

    parser = argparse.ArgumentParser(description='Monitor for chia nodes.')
    parser.add_argument('-c', '--config', type=str, required=True, help="Path to config file.")
    parser.add_argument('-m', '--manual', type=str, required=False, nargs='+', help="Run plugin manually on startup.")
    args = parser.parse_args()

    with open(args.config, "r") as stream:
        config = yaml.safe_load(stream)
    
    outputs = {}
    plugins = {}

    scheduler = Scheduler()

    output_configs = config['outputs']
    if 'discordbot' in output_configs:
        print(prefix.format('Loading output "Discordbot"...'))
        discordbot_config = os.path.join(os.path.dirname(args.config), output_configs['discordbot'])
        discordbot = Discordbot(discordbot_config)
        await discordbot.start(loop)
        outputs['discordbot'] = discordbot

    plugins_configs = config['plugins']
    for key in plugins_configs:
        if key not in available_plugins:
            print(prefix.format(f'WARNING: plugin {key} given in config, but not available.'))
            continue
        subconfig_path = os.path.join(os.path.dirname(args.config), plugins_configs[key])
        if not os.path.exists(subconfig_path):
            print(prefix.format(f'WARNING: not config file available for plugin {key}.'))
            continue
        plugins[key] = available_plugins[key](subconfig_path, scheduler, outputs.values())


    manual_tasks = []
    for manual_plugin in args.manual:
        print(prefix.format(f'Manual run of plugin {manual_plugin}.'))
        manual_tasks.append(scheduler.manual(manual_plugin))
    await asyncio.gather(*manual_tasks)

    print(prefix.format('Startup complete.'))

    await schedule_plugins(scheduler)

async def schedule_plugins(scheduler):
    while True:
        time.sleep(60)
        await scheduler.run()

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(main())
    finally:
        loop.close()