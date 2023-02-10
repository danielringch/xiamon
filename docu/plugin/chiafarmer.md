# The Xiamon chia farmer plugin

This plugin monitors the chia farmer.

## **Configuration template**

The basic configuration information can be found [here](../config_basics.md).

```yaml
name: "my_chiafarmer"  #unique name
summary_interval: "0 0 * * *"  #cron schedule expression
alert_mute_interval: 24  #hours
underharvested_threshold_short: 0.92  #factor
underharvested_threshold_long: 0.99  #factor
host: "127.0.0.1:8559"
cert: "~/.chia/mainnet/config/ssl/full_node/private_farmer.crt"
key: "~/.chia/mainnet/config/ssl/full_node/private_farmer.key"
```

## **Connect the full node**

Communication with the chia farmer is done via the chia API. Since the connection uses SSL, the key and the cert file are required.

The **host** of the chia farmer is usually **127.0.0.1:8559**. If the chia api shall be accessed from another machine in the network, the key **self_hostname** in the chia configuration needs to be set to **0.0.0.0**.

The cert file can be usually found here: `~/.chia/mainnet/config/ssl/full_node/private_farmer.crt`.

The key file can be usually found here: `~/.chia/mainnet/config/ssl/full_node/private_farmer.key`.

## **Checks**

The plugin checks the challenges processed by the farmer for missing signage points. From this information, two harvest factors are calculated:

The short term harvest factor is calculated from the challenges of the last hour. A value of 1 means that no signage points were missing. If the values drops below the treshold configured by the key **underharvested_threshold_short**, an alert is sent.

The long term harvest factor is calculated from the challenges since the last summary. A value of 1 means that no signage points were missing. If the values drops below the treshold configured by the key **underharvested_threshold_long**, an alert is sent.

## **Summary**

A summary is sent to the **info** channel with the average harvest factor since the last summary.

The [execution interval](../config_basics.md) is set by the key **summary_interval**.
