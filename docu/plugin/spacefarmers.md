# The Xiamon spacefarmers plugin

This plugin monitors your whole farm at spacefarmers.io. The online API of spacefarmers.io is used, which means this plugin can run on any computer in the world, as long as it has an internet connection.

## **Configuration template**

The basic configuration information can be found [here](../config_basics.md).

```yaml
name: "my_spacefarmers"  #unique name
summary_interval: "0 0 * * *"  #cron schedule expression
check_interval: "0 * * * *"  #cron schedule expression
alert_mute_interval: 24  #hours
launcher_id: "1cd80c9d73b433a3ac080e50542ffc18bc68dd5b686fbc91866ae90ab2d76f70"
harvesters:
  c0e81b8f13:  #optional
    maximum_offline_time: 0.5 #hours
  97e4fd0301:  #optional
    maximum_offline_time: 1.0 #hours
```

## **Basic setup**

The farm is configured by its launcher_id with the key **launcher_id**.

Harvesters which are added to the key **harvesters** get monitored for their online status and partials. The hash of the harvester can be taken from
the spacefarmers harvesters tab in the dashboard.

The **maximum_offline_time** sets how many hours a harvester can not submit a partial until it is detected as offline. The necessary values for not getting false positive alerts depends on the set difficulty and the harvested size. Some try and error might be necessary here to get good values.

## **Check**

The plugin checks the status of all configured harvesters and sends an alert if a harvester is detected as offline.

The [execution interval](../config_basics.md) is set by the key **check_interval**.

## **Summary**

A summary is sent to the **info** channel and contains the following information:

- 24h netspace of the whole farm
- Earnings since last summary
- Partials for all monitored harvesters
- Average partial times for all monitored harvesters

The [execution interval](../config_basics.md) is set by the key **summary_interval**.
