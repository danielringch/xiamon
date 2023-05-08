# The Xiamon discordbot interface

This interface writes messages to discord using a discord bot.

An explanation how to create a discord bot can be found [here](https://discordpy.readthedocs.io/en/stable/discord.html).

## **Configuration template**

```yaml
token: "tokens/my_discordbot.token"  #path is relative to location of this config file
alert:  #optional
  id: 123456789012345678
info:  #optional
  id: 234567890123456789
verbose:
  id: 345678901234567890
accounting:  #optional
  id: 456789012345678901
  whitelist:  #optional
    - "my_storagenode"
error:  #optional
  id: 567890123456789012
debug:  #optional
  id: 678901234567890123
  blacklist:  #optional
    - "my_systemmonitor"
    - "my_pingdrive"
```

## **Connect the bot**

The token of the bot needs to be stored in a text file. The path to this file is configured by the key **token**.

Each instance of this plugin needs its own discord bot.

## **Configuring the channels**

The channels can be configured individually by giving the corresponding keys in the configuration file. If a channel is omitted, the interface will ignore this channel.

The id of the discord channel is configured by the key **id**. A short video how to get the id of a discord channel can be found [here](https://www.youtube.com/watch?v=YjiQ7CajAgg). Discord channels can be reused for multiple channels in Xiamon.

If the key **whitelist** is given, all messages from plugins which instance names are not in the whitelist are ignored for the corresponding channel.

If the key **blacklist** is given, If given, all messages from plugins which instance names are in the list are ignored for the corresponding channel.

(Of course, it does only make sense to use either a whitelist or a blacklist for a channel.)