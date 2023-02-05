# The Xiamon smartctl plugin

This plugin checks the drive health using the S.M.A.R.T. data of the drives.

## **Configuration template**

The basic configuration information can be found [here](../config_basics.md).

```yaml
name: "my_smartctldrive"  #unique name
check_interval: "0 * * * *"  #cron schedule expression
report_interval: "0 0 * * MON"  #cron schedule expression
binary: "~/smartctl"
database: database: "~/myDb.sqlite"
aggregation: 24  #hours
expiration: 31  #days
limits:  #optional
    4:
        evaluation: delta_max
        value: 1
    5:
        evaluation: delta_max
        value: 0
    193:
        evaluation: delta_max
        value: 50
    197:
        evaluation: delta_max
        value: 0
drives:  #optional
    "ST14000NM001G-2K_ABCDEFGH":
        alias: my_drive_1  #optional
        limits:  #optional
            194:
              evaluation: max
              value: 40
    "TOSHIBA_MG09ACA1_ABCDEFGH":
        alias: my_drive_2  #optional
        limits:  #optional
            194:
              evaluation: max
              value: 45
blacklist:
    - "Generic_0123456789ABCDEF"
```

## **Basic setup**

This plugin calls the program `smartctl` from smartmontools, which requires root rights. Since it is not useful to run Xiamon as root, it is necessary to make `smartctl` usable with the user running Xiamon:

- as root, copy the smartctl binary (usually in /usr/sbin) to a place accessible by the user running Xiamon
- as root, make the copy of `smartctl` executable for the user running Xiamon by running the command `chmod u+s smartctl`
- Set the value of the key **binary** in the configuration to the path of the copy of `smartctl`

The plugin stores the S.M.A.R.T. data from the drives in its own database. The path of the file is set by the key **database**.

The plugin is capable of checking the delta of S.M.A.R.T. data. The reference time is configured by the key **aggregation**. E.g. a value of 24 means that the delta check compares S.M.A.R.T. data with the data from 24 hours ago.

To prevent the database from getting too big, old data is removed automatically. The time how long data remains in the database is configured by the key **expiration**.

## **Global checks**

There are usually some S.M.A.R.T. attributes that shall be checks for all drives (e.g. reallocated sectors count). These checks are added to the global checks configured by the key **limits**.

Per attribute, a new key containing the attribute ID is added. Common IDs can be found [here](https://en.wikipedia.org/wiki/Self-Monitoring,_Analysis_and_Reporting_Technology#Known_ATA_S.M.A.R.T._attributes).

For each attribute, the type of check is configured by the key **evaluation**. The treshold is configured by the key **value**.

The following types of checks are implemented:

- `max`: the value must not exceed the treshold
- `min`: the value must not fall below the treshold
- `delta_max`: the delta of the value (see **aggregation**) must not exceed the treshold
- `delta_min`: the delta of the value (see **aggregation**) must not fall below the treshold

## **Drive identifiers**

Custom checks per drive and the blacklist use drive identifiers. There are two ways to get the identifier of a drive:

1. Run Xiamon with this plugin configured. All drives with their identifiers will be listed on the **debug** channel on startup.
2. Run `lsblk -o MODEL,SERIAL` and connect both values with an underscore.

For better readability, an alias for each drive can be configured, see next section.

## **Custom checks**

For each drive, custom checks can be configured. Both adding new checks and overwriting global checks is supported. Furthermore, an alias for the drive can be added. 

It is possible to only set the alias for a drive without configuring any custom check.

Custom checks are added below the **drives** key in the configuration. For each drive with a custom check (or alias), a new key containing the drive identifier is added.

Below that key, the alias can be configured by the key **alias**. Custom checks can be added the same way as in the global checks.

## **Blacklist**

If a drive shall be ignored by this plugin (this is often the case for SSDs), their drive identifier can be added to the blacklist configured by the key **blacklist**.

## **Checks**

The plugin periodically fetches the S.M.A.R.T. data of the drives and runs the configured check. For each failed check, an alert is sent.

Please note that no alert is sent if the drive is not available or reading its S.M.A.R.T. data failes.

The [execution interval](../config_basics.md) is set by the key **check_interval**.

## **Reports**

A summary is sent to the **report** channel with a table containing all drives and their monitored S.M.A.R.T. data.

The [execution interval](../config_basics.md) is set by the key **report_interval**.
