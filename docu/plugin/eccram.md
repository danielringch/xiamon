# The Xiamon eccram plugin

This plugin checks the error statistics of ECC RAM and sends alerts if any correctable or uncorrectable error was detected by the system.

## **Prerequisites**

This plugin needs linux with the EDAC kernel module loaded. ECC RAM is also required.

If the plugin is not able to read the ECC RAM error statistics, a message is sent to the **error** channel.

## **Configuration template**

The basic configuration information can be found [here](../config_basics.md).

```yaml
name: "my_eccram"  #unique name
interval: "0 0 * * *"  #cron schedule expression
```

## **Check**

The plugin checks the number of correctable or uncorrectable errors of every memory controller of the system.

If any of these numbers increased since the last check, an **alert** is sent.
