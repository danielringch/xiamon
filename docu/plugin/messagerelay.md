# The Xiamon messagerelay plugin

This plugin allows you to add external software to the Xiamon messaging infrastructure. Messages can be sent to an HTTP server as a POST request. They will then be sent to the interfaces.

## **Configuration template**

The basic configuration information can be found [here](../config_basics.md).

```yaml
name: "my_messagerelay"  #unique name
host: "localhost"  #ip
port: "8080"  #port
```

## **Basic setup**

The key **host** sets the address the HTTP server is listening to.

The key **port** sets the port the HTTP server is listening to.

## **Sending messages**

Messages are sent to this plugin via an HTTP POST request, containing a JSON payload:

```json
{
  "sender": "my_external_sender",
  "channel": "info",
  "message": "Hello, world!"
}
```

The **sender** will be shown as the sender of the message. It can be compared to the name of the plugins. The interface whitelists and blacklists can be used to filter senders.

The **channel** sets the target channel. Possible values are:
- alert
- info
- verbose
- accounting
- error
- debug

The **message** contains the message that will be sent.

If the received POST request was valid, status code 200 will be responded. In case of any error, the response will have status code 400.
