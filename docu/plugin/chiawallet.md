# The Xiamon chia wallet plugin

This plugin monitors the chia full wallet. Both lite wallet and wallet as part of a full node setup are supported.

## **Configuration template**

The basic configuration information can be found [here](../config_basics.md).

```yaml
name: "my_chiawallet"  #unique name
check_interval: "*/5 * * * *"  #cron schedule expression
summary_interval: "0 0 * * *"  #cron schedule expression
alert_mute_interval: 24  #hours
cert: "~/.chia/mainnet/config/ssl/full_node/private_wallet.crt"
key: "~/.chia/mainnet/config/ssl/full_node/private_wallet.key"
host: "127.0.0.1:9256"
wallet_id: 1
database: "~/myDb.sqlite"
csv_export: "~/myCsv.csv"  #optional
currency: "usd"  #supported: eur,usd
```

## **Basic setup**

To track the wallet balance, this plugin uses an internal database. The path of the file is set by the key **database**.

Currently, only XCH is supported (support for other CATs will follow). The corresponding wallet id is set by the key **wallet_id**.

Finally, the desired fiat currency has to be set by the key **currency**. The currencies `eur` and `usd` are supported.

## **Connect the wallet**

Communication with the chia wallet is done via the chia API. Since the connection uses SSL, the key and the cert file are required.

The **host** of the chia wallet is usually **127.0.0.1:9256**. If the chia api shall be accessed from another machine in the network, the key **self_hostname** in the chia configuration needs to be set to **0.0.0.0**.

The cert file can be usually found here: `~/.chia/mainnet/config/ssl/full_node/private_wallet.crt`.

The key file can be usually found here: `~/.chia/mainnet/config/ssl/full_node/private_wallet.key`.

## **Checks**

The plugin checks the wallet balance periodically. 

If the wallet is not synced, an alert is sent.

If the wallet balance has changed, a message is sent to the channels **info** and **report**. If the key **csv_export** is set, the balance change is also added to a CSV export file.

The [execution interval](../config_basics.md) is set by the key **check_interval**.

## **Summary**

A summary is sent to the **info** and **report** channels and contains the following information:

- Wallet balance
- Coin price

The [execution interval](../config_basics.md) is set by the key **summary_interval**.

