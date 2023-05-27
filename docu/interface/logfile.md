# The Xiamon logfile interface

This interface writes messages to text files.

## **Configuration template**

```yaml
alert:  #optional
  file: "~/logs/alert.log"
info:  #optional
  file: "~/logs/info.log"
verbose:  #optional
  file: "~/logs/verbose.log"
accounting:  #optional
  file: "~/logs/accounting.log"
  sort_by_plugin: true  #optional
  whitelist:  #optional
    - "my_storagenode"
error:  #optional
  file: "~/logs/other.log"
debug:  #optional
  file: "~/logs/other.log"
  blacklist:  #optional
    - "my_systemmonitor"
    - "my_pingdrive"
```

## Configuring the channels

The channels can be configured individually by giving the corresponding keys in the configuration file. If a channel is omitted, the interface will ignore this channel.

The location of the logfiles is configured by the key **file** and is given as absolute path. The interface will append dates or plugin names to the base name. The same path can be used for multiple channels.

If the key **sort_by_plugin** is given and set to true, the interface will create one file per plugin. Otherwise, the interface will create one file per day.

If the key **whitelist** is given, all messages from plugins which instance names are not in the whitelist are ignored for the corresponding channel.

If the key **blacklist** is given, If given, all messages from plugins which instance names are in the list are ignored for the corresponding channel.

(Of course, it does only make sense to use either a whitelist or a blacklist for a channel.)