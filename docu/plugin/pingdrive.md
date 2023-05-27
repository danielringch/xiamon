# The Xiamon pingdrive plugin

This plugin checks drive activity and availability. 

## **Introduction**

This plugin is primarily created for chia farming.

Farming chia produces very little disk activity. Depending on the number of plot files, the intervals between two disk accesses can get long enough to park the heads of the hard disk. As a result, the load cycle count increases and the lifespan of the disk is reduced. This plugin pings the drives by reading a small amount of plot data, preventing the heads from parking.

Drives might go offline due to a failure or just an unmount event. This plugin sends an alert if it fails to access a disk.

Furthermore, the minutes with disk activity are tracked. If the plots of the drives are not farmed due to misconfguration or other errors, it results in too little disk activity.

## **How it works**

For the list of drives given in the configuration, this plugins checks the bytes read and written on the corresponding block device. If no access happened for a given time period, a random small part of a chia plot file is read (a ping is performed), which leads to a read access (it is _very_ unlikely that this part of the file is in the cache). If the ping failed, the drive is detected offline and an alert is sent.

## **Configuration template**

The basic configuration information can be found [here](../config_basics.md).

```yaml
name: "my_pingdrive"  #unique name
summary_interval: "0 0 * * *"  #cron schedule expression
alert_mute_interval: 24  #hours
drives:
    - my_drive_1:
        mount_point: "/mnt/foo"
        path_to_plots: "/mnt/foo/plots"
        max_idle_time: 5  #minutes
        expected_active: 250  #minutes
    - my_drive_2:
        mount_point: "/mnt/bar"
        path_to_plots: "/mnt/bar/plots"
        max_idle_time: 3  #minutes
        expected_active: 200  #minutes
```

## **Drive setup**

For each drive which should be monitored, a list entry is added to the key **drives**.

The key of a list item is the **drive alias**. It is used in the messages sent by the plugin.

The key **mount_point** sets the mount of the drive. In case the drive has multiple mount points, an arbitrary mount point can be given (as long as it contains plot files).

The key **path_to_plots** sets the directory where plots files are read to generate disk activity.

The key **max_idle_time** sets the maximum time in minutes a drive can be idle, before a read access is issued by this plugin.

The key **expected_active** sets the number of minutes the drive is expected to be active in normal operation. A value of 10 does mean that there should be 10 of the monitored minutes where a disk activity happened.

## **Summary**

A summary is sent to the **info** channel with the following information:

- Number of drives
  - online (everything is okay)
  - inactive (ping is successful, but number of expected active minutes was not reached)
  - offline (ping failed)

A table with detailed information for every drive is sent to the **verbose** channel.

The [execution interval](../config_basics.md) is set by the key **summary_interval**.
