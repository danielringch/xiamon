# The Xiamon main config file

The Xiamon main confile is a yaml file with the following sections.

A template can be found [here](../xiamon/config/config.yaml_template).

## Interfaces

The key

    interfaces:

is used, followed by the infaces and their individual configuration files. All links are relative to the location of this configuration file.

    interfaces:
      interface1: <myFile1.yaml>    
      interface2: <myFile2.yaml>

If more than one instance of an interface is used, a list of configuration files is given:    

    interfaces:
      interface1: <myFile1.yaml>    
      interface2:
        - <myFile2.yaml>
        - <myFile3.yaml>

The following interfaces are available:

- discordbot
- logfile
- stdout

## Plugins

The key

    plugins

is used, everything else is basically the same as for interfaces.

The following plugins are available:

- chiafarmer
- chianode
- chiawallet
- flexfarmer
- flexpool
- pingdrive
- servicepin>
- siahost
- smartctl
- storjnode
- sysmonitor