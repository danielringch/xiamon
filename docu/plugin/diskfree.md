# The Xiamon diskfree plugin

This plugin checks the free space at configured locations and can also delete files based on a pattern if necessary.
This plugin is mainly intented to be used with expendable data which can be removed if more space is needed. E.g. the free space of a drive used by Sia or Storj may be used by Chia plot files.

## **Configuration template**

The basic configuration information can be found [here](../config_basics.md).

```yaml
name: "my_diskfree"  #unique name
check_interval: "0 0 * * *"  #cron schedule expression
alert_mute_interval: 24  #hours
drives:
    - "/mnt/foo":  #optional
        minimum_space: "10G"  #bytes or percent
        delete: "/mnt/foo/*.txt"  #optional
    - "/mnt/bar":  #optional
        minimum_space: "5%"  #bytes or percent
        delete: "/mnt/bar/*.zip"  #optional
```

## **Setup**

The locations to check are added as list item to the key **drives**. The path is used as key.

Per location, the **minimum_space** can be configured as either a relative (suffix: %) or an absolute (optional suffix: k, M, G, T, P) value.

If the key **delete** is given, files matching the pattern are deleted until the minimum free space is reached again.

## **Check**

The plugin checks the free space of all configured locations.

If a file gets deleted, a message is sent to the **info** channel.

If the free space of a location falls below its minimum value, an **alert** is sent.

The [execution interval](../config_basics.md) is set by the key **check_interval**.
