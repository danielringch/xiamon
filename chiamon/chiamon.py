import argparse, os, yaml, asyncio, time
import warnings
from pytz_deprecation_shim import PytzUsageWarning

from core import *
from interfaces import *
from plugins import *

__version__ = "0.1.0"

warnings.filterwarnings(
    "ignore",
    category=PytzUsageWarning
)

prefix = '[chiamon] {0}'

available_plugins = {'flexfarmer': Flexfarmer}

async def main():
    print(f'Chiamon {__version__}')

    parser = argparse.ArgumentParser(description='Monitor for chia nodes.')
    parser.add_argument('config', metavar='config')
    parser.add_argument('--run-on-startup', action='store_true', dest="on_startup", help="Run all plugins on startup.")
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
        subconfig_path = os.path.join(os.path.dirname(args.config), plugins_configs['flexfarmer'])
        if not os.path.exists(subconfig_path):
            print(prefix.format(f'WARNING: not config file available for plugin {key}.'))
            continue
        plugins[key] = available_plugins[key](subconfig_path, scheduler, outputs.values())

    print('Ready.')

    if args.on_startup:
        await scheduler.force_all()

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