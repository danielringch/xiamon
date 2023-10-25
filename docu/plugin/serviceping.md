# The Xiamon serviceping plugin

This plugin pings some services to check whether they are online. This plugin usually runs on another computer in your local network to detect if your server crashes. The following services are supported:
- chia (full node)
- sia (siad)
- storj

## **Configuration template**

The basic configuration information can be found [here](../config_basics.md).

```yaml
name: "my_serviceping"  #unique name
summary_interval: "0 0 * * *"  #cron schedule expression
check_interval: "0 * * * *"  #cron schedule expression
alert_mute_interval: 24  #hours
hosts:
    my_host_1:  # optional
        type: chia
        cert: "~/.chia/mainnet/config/ssl/full_node/private_full_node.crt"
        key: "~/.chia/mainnet/config/ssl/full_node/private_full_node.key"
        host: "127.0.0.1:8555"
    my_host_2:  # optional
        type: sia
        host: "127.0.0.1:9980"
    my_host_3:  # optional
        type: storj
        host: "127.0.0.1:14002"
```

## **Basic setup**

The services to monitor are listed under the key **hosts**. For each service, the displayed name is set as a key.

The key **type** sets the type of service, supported values are `chia`, `sia` and `storj`.

### ***Chia***

The configuration is the same as for the chia full node plugin and can be found [here](chianode.md).

### ***Sia***

The key **host** specifies the ip and port of the siad instance. For more information, see the documentation of the [siahost plugin](siahost.md). No api password is required for this plugin.

### ***Storj***

The key **host** specifies the ip and port of the storj instance. For more information, see the documentation of the [storj plugin](storjnode.md).


## **Check**

The configured services are pinged with a corresponding lightweight API call. If a service does not respond, an alert is sent.

The [execution interval](../config_basics.md) is set by the key **check_interval**.

## **Summary**

A summary is sent to the **info** channel and contains the following information:

- Number of successful pings per service
- Number of failed pings per service

The [execution interval](../config_basics.md) is set by the key **summary_interval**.

