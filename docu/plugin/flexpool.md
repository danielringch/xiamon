# The Xiamon flexpool plugin

This plugin monitors your whole farm at flexpool. The online API of flexpool is used, which means this plugin can run on any computer in the world, as long as it has an internet connection.

## **Configuration template**

The basic configuration information can be found [here](../config_basics.md).

```yaml
name: "my_flexpool"  #unique name
summary_interval: "0 0 * * *"  #cron schedule expression
check_interval: "0 * * * *"  #cron schedule expression
alert_mute_interval: 24  #hours
address: "xch1fh6f088cxcvqscy4xtxfq7762vhsh9mjcql6m3svfhmlxsc3jd4sd37xdl"
currency: "USD"
worker_blacklist:  #optional
  - "my_unimportant_worker"
```

## **Basic setup**

The farm is configured by its payoutaddress with the key **address**.

The desired fiat currency is set by the key **currency**. The currencies `EUR` and `USD` are supported.

If the netspace of a worker is too small, it might get detected offline by flexpool from time to time. In this case, it can be added to the **worker_blacklist**.

## **Check**

The plugin checks the status of all workers and sends an alert if a worker is detected as offline by flexpool.

The [execution interval](../config_basics.md) is set by the key **check_interval**.

## **Summary**

A summary is sent to the **info** channel and contains the following information:

- Open balance
- Worker overview
    - Reported/ average hashrate
    - Valid/ stale/ invalid partials
- Payments since last summary

The [execution interval](../config_basics.md) is set by the key **summary_interval**.
