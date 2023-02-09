# The Xiamon sysmonitor plugin

This plugin monitors a storj SNO instance.

## **Configuration template**

The basic configuration information can be found [here](../config_basics.md).

```yaml
name: "my_storagenode"  #unique name
check_interval: "*/15 * * * *"  #cron schedule expression
summary_interval: "0 0 * * *"  #cron schedule expression
report_interval: "0 0 3 * *"  #cron schedule expression
alert_mute_interval: 24  #hours
host: "127.0.0.1:14002"
database: "~/myDb.sqlite"
csv_export: "~/myCsv.csv"  #optional
```

## **Basic setup**

The storjhost is usually `127.0.0.1:14002` and is configured by the key **host**.

The plugin uses an internal database, its path is configured by the key **database**.

## **Checks**

The plugin checks the health of the storj instance and sends an alert if one of the following conditions are true:

- Software version is outdated
- QUIC is not enabled
- No satellite is connected
- Node is suspended or disqualified by a satellite
- Storage space is overused

The [execution interval](../config_basics.md) is set by the key **check_interval**.

## **Summary**

A summary is sent to the **info** channel, containing the following information:

- Storage utilization
- Egress traffic since last summary
- Ingress traffic since last summary
- Repair/ audit traffic since last summary
- Earnings since last summary (exlcuding held earnings)
- Total earnings of the month (exlcuding held earnings)

Traffic information is not available if the month changes between two summaries.

The [execution interval](../config_basics.md) is set by the key **summary_interval**.

## **Report**

A summary is sent to the **report** channel, containing the following information about the last month:

- Storage utilization
- Egress traffic
- Repair/ audit traffic since last summary
- Earnings for all three categories
- Held earnings
- Total earnings

If the key **csv_export** is set, the rewards are also added to a CSV export file.

The necessary information may not be available from storj directly after the new month has started. Triggering the report on the third day of the next month or later has shown to work fine.

The [execution interval](../config_basics.md) is set by the key **report_interval**.