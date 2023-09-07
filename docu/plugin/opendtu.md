# The Xiamon opendtu plugin

This plugin monitors Hoymiles solar invertes connected to an [openDTU](https://github.com/tbnobody/OpenDTU).

## **Configuration template**

The basic configuration information can be found [here](../config_basics.md).

```yaml
name: "my_opendtu"  #unique name
check_interval: "0 * * * *"  #cron schedule expression
summary_interval: "0 0 * * *"  #cron schedule expression
alert_mute_interval: 24  #hours
host: "192.168.4.1:80"
database: "~/myDb.sqlite"
verbose_csv_export: "~/myVerboseCsv.csv"  #optional
summary_csv_export: "~/mySummaryCsv.csv"  #optional
```

## **Basic setup**

For the key **host**, you need ip address and port of your openDTU. The ip address depends on your network setup, while the port is usually `80`.

The plugin uses an internal database, its path is configured by the key **database**.

## **Checks**

The plugin checks the energy statistics and saves them to its database. If the key **verbose_csv_export** is set, the data is also dumped into a csv file.

No alerts are sent in any case.

The [execution interval](../config_basics.md) is set by the key **check_interval**.

## **Summary**

A summary is sent to the **info** channel, containing the following information:

- Fed-in energy since last summary
- Total fed-in energy

This data is also dumped into a csv file, if the key **summary_csv_export** is set.

A table with more detailed information is sent to the **verbose** channel.

The [execution interval](../config_basics.md) is set by the key **summary_interval**. It is strongly recommended to trigger the summary at night when the inverter is offline; otherwise, the results may be incorrect.
