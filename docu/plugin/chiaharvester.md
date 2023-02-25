# The Xiamon chia harvester plugin

This plugin monitors the chia harvester.

## **Configuration template**

The basic configuration information can be found [here](../config_basics.md).

```yaml
name: "my_chiaharvester"  #unique name
interval: "0 * * * *"  #cron schedule expression
alert_mute_interval: 24  #hours
host: "127.0.0.1:8560"
cert: "~/.chia/mainnet/config/ssl/full_node/private_harvester.crt"
key: "~/.chia/mainnet/config/ssl/full_node/private_harvester.key"
```

## **Connect the full node**

Communication with the chia harvester is done via the chia API. Since the connection uses SSL, the key and the cert file are required.

The **host** of the chia harvester is usually **127.0.0.1:8560**. If the chia api shall be accessed from another machine in the network, the key **self_hostname** in the chia configuration needs to be set to **0.0.0.0**.

The cert file can be usually found here: `~/.chia/mainnet/config/ssl/full_node/private_harvester.crt`.

The key file can be usually found here: `~/.chia/mainnet/config/ssl/full_node/private_harvester.key`.

## **Checks**

The plugin checks the harvester for any invalid or missing plot files. If any of those plot files is found, an alert is sent.

The [execution interval](../config_basics.md) is set by the key **interval**.
