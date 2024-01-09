# The Xiamon mqttlogger plugin

This plugin connects to an MQTT broker and logs data from configured topics using Xiamons message system.

## **Configuration template**

The basic configuration information can be found [here](../config_basics.md).

```yaml
name: "my_mqtt_logger"  #unique name
host: "localhost:1883"  #ip, port
ca: "foo.crt"  #optional, path to CA certificate
tls_insecure: false  #optional, may be necessary to allow self signed certificates
user: "foo"  #optional, MQTT broker user
password: "bar"  #optional, MQTT broker user
topics:
    foo/bar: #optional, MQTT topic
        channel: info  #xiamon message channel
        type: uint8  #type hint
    test/123: #optional, MQTT topic
        channel: alert  #xiamon message channel
        type: utf-8  #type hint
```

## **Basic setup**

The key **host** sets IP and port of the MQTT broker.

For a TLS secured connection to the MQTT broker, the key **ca** sets the path to the CA cert file. If a self signed certificate is used, you might need to set the key **tls_insecure** to `true`.

If the MQTT broker required login credentials, use the keys **user** and **password**.

## **Subscribing topics**

All topics this plugin shall subscribe are added under the key **topics**.

The **channel** sets the target channel. Possible values are:
- alert
- info
- verbose
- accounting
- error
- debug

The **type** specifies the type of data received on the channel. Possible values are:
- bool
- uint8
- int8
- uint16
- int16
- uint32
- int32
- uint64
- int64
- float
- double
- utf8
