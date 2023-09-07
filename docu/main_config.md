# The Xiamon main config file

The Xiamon main configuration file defines the used plugins, interfaces and their corresponding configuration files.

It must be named `xiamon.yaml`.

## **Configuration template**

```yaml
interfaces:
  discordbot: "interface/discordbot.yaml"  #optional
  logfile: "interface/logfile.yaml"  #optional
  stdout: "interface/stdout.yaml"  #optional
plugins:
  chiafarmer: "plugin/.yaml"  #optional
  chiaharvester:  #optional
    - "plugin/chiaharvester_1.yaml"
    - "plugin/chiaharvester_2.yaml"
  chianode: "plugin/chianode.yaml"  #optional
  chiawallet: "plugin/chiawallet.yaml"  #optional
  diskfree: "plugin/diskfree.yaml"  #optional
  eccram: "plugin/eccram.yaml"  #optional
  flexfarmer: "plugin/flexfarmer.yaml"  #optional
  flexpool: "plugin/flexpool.yaml"  #optional
  messagerelay: "plugin/messagerelay.yaml"  #optional
  opendtu: "plugin/opendtu.yaml"  #optional
  pingdrive: "plugin/pingdrive.yaml"  #optional
  serviceping: "plugin/serviceping.yaml"  #optional
  siahost: "plugin/siahost.yaml"  #optional
  smartctl: "plugin/smartctl.yaml"  #optional
  storjnode: "plugin/storjnode.yaml"  #optional
  sysmonitor: "plugin/sysmonitor.yaml"  #optional
```

The key **interfaces** starts the section defining the interfaces Xiamon uses as outputs. The subsequent key defines the interface, for each given configuration file, an own instance of the interface is created.

The following interfaces are available:

- discordbot
- logfile
- stdout

The key **plugins** starts the section defining the plugins. The subsequent key defines the plugin, for each given configuration file, an own instance of the plugin is created.

The following plugins are available:

- chiafarmer
- chiaharvester
- chianode
- chiawallet
- diskfree
- eccram
- flexfarmer
- flexpool
- messagerelay
- opendtu
- pingdrive
- serviceping
- siahost
- smartctl
- storjnode
- sysmonitor