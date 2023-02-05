# The Xiamon chia full node plugin

This plugin monitors the chia full node.

## **Configuration template**

The basic configuration information can be found [here](../config_basics.md).

```yaml
name: "my_chianode"  #unique name
summary_interval: "0 0 * * *"  #cron schedule expression
check_interval: "0 * * * *"  #cron schedule expression
alert_mute_interval: 24  #hours
host: "127.0.0.1:8555"
cert: "~/.chia/mainnet/config/ssl/full_node/private_full_node.crt"
key: "~/.chia/mainnet/config/ssl/full_node/private_full_node.key"
```

## **Connect the full node**

Communication with the chia full node is done via the chia API. Since the connection uses SSL, the key and the cert file are also necessary.

The **host*** of the chia full node is usually **127.0.0.1:8555**. If the chia api shall be accessed from another machine in the network, the key **self_hostname** in the chia configuration needs to be set to **0.0.0.0**.

The cert file can be usually found here: `~/.chia/mainnet/config/ssl/full_node/private_full_node.crt`.

The key file can usually found here: `~/.chia/mainnet/config/ssl/full_node/private_full_node.key`

## **Checks**

The plugin checks whether the full node is synced and sends an alert if the full node is not synced.

The [execution interval](../config_basics.md) is set by the key **check_interval**.

## **Summary**

A summary is sent to the **info** channel and contains the following information:

- Sync status with height
- Connected nodes/ wallets/ etc.

The [execution interval](../config_basics.md) is set by the key **summary_interval**.
