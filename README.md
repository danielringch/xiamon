# Xiamon - a chia/ sia/ storj rig monitor

Xiamon is a multi-purpose computer monitoring software for running storage based web3 and crypto services, such as chia, sia and storj.

The focus of the software is to minimize the necessary effort to keep your rig running - no fancy diagrams, no customizable dashboard, but realtime notifications if something is wrong. 

Xiamon does not only monitor the services itself, but can also keep an eye on your system at all.

The individual functionality, as well as the outputs, is provided using plugins. So each user can select individual plugins and outputs depending on their needs.

## **Prerequisites**

Xiamon needs python3 installed and is tested for Ubuntu and Debian/ Raspbian. Linux in general should work fine, feedback is appreciated.

Even less powerful hardware, such as the Raspberry Pi Zero, is more than enough to run this tool.

## **Plugings**

- Chia
  - [chiaharvester](docu/plugin/chiaharvester.md): Chia harvester monitoring using the chia API. Checks for problems with the plot files.
  - [chiafarmer](docu/plugin/chiafarmer.md): Chia farmer monitoring using the chia API. Checks for missed signage points and problems with the plot files.
  - [chianode](docu/plugin/chianode.md): Chia full node monitoring using the chia API. Checks that the nodes stays synced and gives information about connected peers.
  - [chiawallet](docu/plugin/chiawallet.md): Chia (lite) wallet monitoring using the chia API. Tracks the wallet balance and its changes.
  - [flexfarmer](docu/plugin/flexfarmer.md): Flexfarmer instance monitoring using flexfarmer log files. Gives statistics about points, space and lookup times.
  - [flexpool](docu/plugin/flexpool.md): Flexpool account monitoring using flexpool API. Tracks the open balance and worker status.
- Sia
  - [siahost](docu/plugin/siahost.md): Sia host monitoring using the sia API. Includes wallet tracking, storage and traffic statistics, automatic price updates and financial reporting.
- Storj
  - [storjnode](docu/plugin/storjnode.md): Storj node monitoring using the storj API. Includes storage and traffic statistics and financial reporting.
- Drive management
  - [pingdrive](docu/plugin/pingdrive.md): Supervises disk activity and pings drive if too inactive. Prevents head parking and alerts in case of drives going offline.
  - [smartctl](docu/plugin/smartctl.md): Checks drive health using S.M.A.R.T. and provides some logging.
- General
  - [sysmonitor](docu/plugin/sysmonitor.md): Checks basic system health, such as load, RAM, Swap and temperatures
  - [serviceping](docu/plugin/serviceping.md): Pings chia, sia, storj and flexfarmer using their APIs. Usefull to check from another machine that your service is online.

### Plugins planned for the future

- eccram: supervices the ecc ram error statistics
- and some more

## Outputs

Xiamon communicates with outputs. Messages are routed through different channels, depending on their content:

- **Alert**: Something unusal happened. It is a good idea to configure Xiamon to send messages from this channel to an output giving you instant messages.

- **Info**: Some nice summaries and statistics. Nothing urgent.

- **Report**: Summaries and statistics worth to archive. Often used for financial reporting.

- **Error**: Something is wrong with the tool. Either your configuration file contains a mistake our you found a bug.

- **Debug**: Some verbose outputs. Most of them should not be relevant for most users.

The following outputs are available:

- [Console output](docu/interface/stdout.md)
- [Log file](docu/interface/logfile.md)
- [Discord  bot](docu/interface//discordbot.md)

More outputs can be added easily in the future.

## Installation


1. Clone this repository: `git clone https://github.com/danielringch/xiamon.git`
2. Copy the `config` directory to a place of your choise
3. Adapt the copied config files
4. Install dependencies: `python3 -m pip install -r requirements.txt`
5. Run Xiamon



## Configuration

The configuration is done via yaml files. One main yaml file contains global settings, the used plugins/ outputs and their configuration files. Every plugin of an plugin/ instance has an additional own configuration file.

Further documentation can be found [here](docu/main_config.md); the documentation of the plugin/ output configuration files can be found in the documentation of the individual plugins/ outputs. There are also template configuration files for every plugin/ interface available.

## Usage

Basic usage:

```
python3 xiamon/xiamon.py --config <path to main config file> 
```

It is also possible to trigger some plugin functions at the beginning of the execution. The necessary job identifiers can be taken from the scheduler debug output.

```
python3 xiamon/xiamon.py --config <path to main config file> --manual <job identifier>
```
