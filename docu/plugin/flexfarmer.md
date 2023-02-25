# The Xiamon flexfarmer plugin

This plugin evaluates the flexfarmer log files. 

## **Configuration template**

The basic configuration information can be found [here](../config_basics.md).

```yaml
name: "my_flexfarmer"  #unique name
interval: "0 0 * * *"  #cron schedule expression
log_file: "~/flexfarmer.log"
output_path: "~/myArchive"
```

## **Basic setup**

The path of the flexfarmer log file is set by the key **database**.

All entries looking like an error message are archived by the plugin. This makes it possible to spot things like corrupt plot files etc. easily. The directory to the archive is set by the key **output_path**.

## **Summary**

A summary is sent to the **info** channel and contains the following information:

- Accepted partials
- Stale partials
- Invalid partials
- Lookup times

The [execution interval](../config_basics.md) is set by the key **interval**.
