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
workers:
  my_worker_1:
    maximum_offline_time: 0.5 #hours
  my_worker_2:
    maximum_offline_time: 1.0 #hours
```

## **Basic setup**

The farm is configured by its payout address with the key **address**.

The desired fiat currency is set by the key **currency**. The currencies `EUR` and `USD` are supported.

Workers which are added to the key **workers** get monitored for their online status.

High difficulty settings can make flexpools offline worker detection unreliable. For that reason, this plugin calculates its own online status based on the timestamp of the last submitted partial. The maximum time period a worker can not send a partial before being detected as offline is set per worker by the key **maximum_offline_time**.

## **Check**

The plugin checks the status of all configured workers and sends an alert if a worker is detected as offline.

The [execution interval](../config_basics.md) is set by the key **check_interval**.

## **Summary**

A summary is sent to the **info** channel and contains the following information:

- Open balance
- Worker overview
    - Reported/ average hashrate
    - Valid/ stale/ invalid partials
- Payments since last summary

The [execution interval](../config_basics.md) is set by the key **summary_interval**.
