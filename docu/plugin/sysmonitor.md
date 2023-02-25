# The Xiamon sysmonitor plugin

This plugin monitors the ressource utilization of the local machine.

## **Configuration template**

The basic configuration information can be found [here](../config_basics.md).

```yaml
name: "my_sysmonitor"  #unique name
interval: "* * * * *"  #cron schedule expression
alert_mute_interval: 24  #hours
load:  #optional
    treshold: 4.0
    hysteresis: 1.0
    samples: 5
ram:  #optional
    treshold: 80  #percent
    hysteresis: 5  #percent
    samples: 5
swap:  #optional
    treshold: 50  #percent
    hysteresis: 5  #percent
    samples: 5
temperature:  #optional
    sensor: "/sys/class/hwmon/hwmon*/temp1_input"
    treshold: 75  #degrees celsius
    hysteresis: 5  #degrees celsius
    samples: 5
```

## **Basic setup**

The [execution interval](../config_basics.md) is set by the key **interval**.

If any parameter exceeds the configured **treshold**, an alert is sent.

To avoid toggling alerts, smoothing of the monitored parameters is available. The key **hysteresis** configures how much the monitored parameters value must decrease to reset an alert. The key **samples** controls how many consecutive measurements are taken to calculate the average parameter value.

## **Finding the temperature source**

The temperature is read directly from the `/sys` kernel interface. The exact location depends on your specific linux distribution and version. Some examples are:

- `/sys/class/hwmon/hwmon*/temp1_input`
- `/sys/class/thermal/thermal_zone0/temp`

On some machines, the location sometimes changes its number after a reboot. In this case, use an asterik instead of the actual number.

