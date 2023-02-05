# Xiamon configuration basics

All plugins and interfaces are independent from each other. However, they share some common configuration keys and principles described on this page.

## Name

Every plugin instance needs a unique instance name, given by the key **id**.

    name: myPlugin

Interfaces do not need instance names.

## Alert muting

To prevent message spam, every alert is muted for a certain time interval even. After this time, the alert will be sent again if the reason is still present. The time interval is set by the key **alert_mute_interval** (in hours).

    alert_mute_interval: 24

This key is not available for all plugins. If available, it can be found in the corresponding template configuration file.

## Execution intervals

Every plugin performs several actions, which are triggered according to a schedule. Some of those schedules are fixed, but most can be configured as [cron schedule expression](https://crontab.guru).

    example_interval: "0 0 * * *"