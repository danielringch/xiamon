# Xiamon - a chia/ sia/ storj rig monitor

Xiamon is a multi-purpose computer monitoring software for running storage based web3 and crypto services, such as chia, sia and storj.

The focus of the software is to minimize the necessary effort to keep your rig running - no fancy diagrams, no customizable dashboard, but realtime notifications if something is fishy. 

Tax reporting is also a big feature of Xiamon. Thanks to logfiles and csv exports, it is easy to keep track of the revenues of the individual services.

The whole software is configured as a combination of plugins and outputs, providing great flexibility.

## **Prerequisites**

- Python version 3.8 or newer with pip + venv

The hardware related plugins will only work on linux. All other should run on any OS, but I have no capacity to test this, so feedback is appreciated. My test machines run Ubuntu and Raspbian.

## **Plugings**

- Chia
  - [chiaharvester](docu/plugin/chiaharvester.md): Chia harvester monitoring using the chia API. Checks for problems with the plot files.
  - [chiafarmer](docu/plugin/chiafarmer.md): Chia farmer monitoring using the chia API. Checks for missed signage points.
  - [chianode](docu/plugin/chianode.md): Chia full node monitoring using the chia API. Checks that the node stays synced and gives information about connected peers.
  - [chiawallet](docu/plugin/chiawallet.md): Chia (lite) wallet monitoring using the chia API. Tracks the wallet balance and balance changes.
  - [flexfarmer](docu/plugin/flexfarmer.md): Flexfarmer instance monitoring using flexfarmer log files. Gives statistics about partials, space and lookup times.
  - [flexpool](docu/plugin/flexpool.md): Flexpool account monitoring using flexpool API. Tracks the open balance and worker status.
  - [spacefarmers](docu/plugin/spacefarmers.md): pool monitoring for spacefarmers.io. Tracks the open balance, partials and worker status.
- Sia
  - [siahost](docu/plugin/siahost.md): Sia host monitoring using the sia API. Includes wallet tracking, storage and traffic statistics, automatic price updates and financial reporting.
- Storj
  - [storjnode](docu/plugin/storjnode.md): Storj node monitoring using the storj API. Includes storage and traffic statistics and financial reporting.
- Drive management
  - [diskfree](docu/plugin/diskfree.md): Disk free space monitoring.
  - [pingdrive](docu/plugin/pingdrive.md): Supervises disk activity and pings drives if too inactive. Prevents head parking and sends alerts in case of drives going offline.
  - [smartctl](docu/plugin/smartctl.md): Checks drive health using S.M.A.R.T. and provides some logging.
- Energy management
  - [opendtu](docu/plugin/opendtu.md): Solar farm monitoring for Hoymiles inverters and openDTU.
- General
  - [eccram](docu/plugin/eccram.md): Checks the error statistics of ECC RAM.
  - [messagerelay](docu/plugin/messagerelay.md): Relays messages received via http post request to the interfaces.
  - [sysmonitor](docu/plugin/sysmonitor.md): Checks basic system health, such as load, RAM, swap and temperatures.
  - [serviceping](docu/plugin/serviceping.md): Pings chia, sia, storj and flexfarmer using their APIs. Usefull to check from another machine that your service is online.

## **Outputs**

Xiamon communicates via outputs. Messages are routed through different message channels, depending on their content:

- **Alert**: Something unusal happened. It is a good idea to configure Xiamon to send messages from this channel to an output giving you instant messages.

- **Info**: Some short summaries and statistics. Nothing urgent.

- **Verbose**: Similar to the info channel, but more verbose. Works best with log files.

- **Accounting**: Summaries and statistics related to financial reporting. It is usually worth to archive messages from this channel in log files.

- **Error**: Something is wrong with the tool. Either your configuration file contains a mistake our you found a bug.

- **Debug**: Some verbose outputs. Most are only relevant for debugging.

The following outputs are available:

- [Console output](docu/interface/stdout.md)
- [Log file](docu/interface/logfile.md)
- [Discord  bot](docu/interface/discordbot.md)

More outputs can be added easily in the future.

## **Usage**

1. Activate virtual environment:
```
source <path to virtual environment>/bin/activate
```
2. Run Xiamon:
```
python3 xiamon/xiamon.py --config <path to main config file> 
```

## **Installation**

1. Clone this repository: 
```
git clone https://github.com/danielringch/xiamon.git
```
2. Copy the `config` directory to a place of your choice.
3. Adapt the copied config files.
4. Create a python venv and install dependencies:
```
python3 -m venv <path to virtual environment>
source <path to virtual environment>/bin/activate
python3 -m pip install -r requirements.txt
```


### **Using Docker**

1. Create an empty directory for the configuration.
2. Get the image:
```
docker pull danielringch/xiamon:latest
```
3. Create the container:
```
docker create -v <directory for configuration>:/userconfig --name xiamon danielringch/xiamon:latest
``` 
3. Run Xiamon. Since the configuration directory is emtpy, it will copy the configuration templates and quit.
```
docker start -i xiamon
```
4. Adapt the copied config files.
5. Run Xiamon.

## **Configuration**

The configuration is done via yaml files. One main yaml file contains global settings, the used plugins/ outputs and their configuration files. Every instance of a plugin has its own configuration file.

Further documentation can be found [here](docu/main_config.md); the documentation of the plugin/ output configuration files can be found in the documentation of the individual plugins/ outputs. There are also template configuration files for every plugin/ interface available.

## **Get support**

You have trouble getting started with Xiamon? Something does not work as expected? You have some suggestions or thoughts? Please let me know.

I have chosen reddit as main communication platform for this project, so please visit [r/xiamon](https://www.reddit.com/r/xiamon/) . You can also DM me: [3lr1ng0](https://www.reddit.com/user/3lr1ng0).

Feel also free to open an issue here on github.

## **Contributing**

If you would like to contribute, please read [CONTRIBUTING.md](CONTRIBUTING.md).
