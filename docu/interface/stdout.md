# The Xiamon stdout interface

This interface writes messages to std output.

## **Configuration template**

```yaml
alert:  #optional
  color: "red"  #optional
info:  #optional
report:  #optional
  color: "yellow"  #optional
  whitelist:  #optional
    - "my_storagenode"
error:  #optional
  color: magenta  #optional
debug:  #optional
  color: cyan  #optional
  blacklist:  #optional
    - "my_systemmonitor"
    - "my_pingdrive"
```

## Configuring the channels

The channels can be configured individually by giving the corresponding keys in the configuration file. If a channel is omitted, the interface will ignore this channel.

The color of messages from a channel can be modified by adding the key **color** to the configuration. This should work for the most terminals, but maybe not for all. The following colors are available:

- black
- red
- green
- yellow
- blue
- magenta
- cyan
- white

If the key **whitelist** is given, all messages from plugins which instance names are not in the whitelist are ignored for the corresponding channel.

If the key **blacklist** is given, If given, all messages from plugins which instance names are in the list are ignored for the corresponding channel.

(Of course, it does only make sense to use either a whitelist or a blacklist for a channel.)