# The Xiamon serviceping plugin

This plugin pings some services to check whether they are online. This plugin usually runs on another computer in your local network to detect if your server crashes. The following services are supported:
- chia (full node)
- sia (siad)
- storj
- flexfarmer

## **Configuration template**

The basic configuration information can be found [here](../config_basics.md).

```yaml
name: "my_serviceping"  #unique name
summary_interval: "0 0 * * *"  #cron schedule expression
check_interval: "0 * * * *"  #cron schedule expression
alert_mute_interval: 24  #hours
chia:  #optional
    cert: "~/.chia/mainnet/config/ssl/full_node/private_full_node.crt"
    key: "~/.chia/mainnet/config/ssl/full_node/private_full_node.key"
    host: "127.0.0.1:8555"
flexfarmer: #optional
    host: "127.0.0.1:8080"
sia: #optional
    host: "127.0.0.1:9980"
storj: #optional
    host: "127.0.0.1:14002"
```

## **Basic setup**

### ***Chia***

The configuration for chia is set by the key **chia**. The configuration is the same as for the chia full node plugin and can be found [here](chianode.md).

### ***Flexfarmer***

The configuration for flexfarmer is set by the key **flexfarmer** and has the **host** as value.

The key **api_server_listen** in flexfarmers configuration file needs to be set to `localhost:8080` (access of same machine) or `0.0.0.0:8080` (access in local network) to enable flexfarmers API server.

The port of the api server in the flexfarmer configuration template is set to 8080. In practice, this port is often already in use by other http servers on the machine, feel free to choose a different port.

### ***Sia***

The configuration for sia is set by the key **sia**. The configuration is the same as for the siahost plugin and can be found [here](siahost.md). Since this plugin only does readonly calls, no api password is required.

### ***Storj***

The configuration for storj is set by the key **storj**. The configuration is the same as for the storj plugin and can be found [here](storj.md).

## **Check**

The configured services are pinged with a corresponding lightweight API call. If a service does not respond, an alert is sent.

The [execution interval](../config_basics.md) is set by the key **check_interval**.

## **Summary**

A summary is sent to the **info** channel and contains the following information:

- Number of successful pings per service
- Number of failed pings per service

The [execution interval](../config_basics.md) is set by the key **summary_interval**.

