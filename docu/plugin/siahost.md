# The Xiamon siahost plugin

This plugin monitors a siad instance used as host.

The main focus of this plugin are health checks, automatic price management and financial/ tax reporting.

One word of caution: dealing with balances in siad is a mess. The data from the wallet and the data from the contracts is not very consistent. For example, the revenues of a day calculated from the contract list does not match the changes of the total balance of the wallet. Not even the locked collateral reported by siad is equal to the sum of locked collateral from the contract list. Siad is deprecated and will be replaced by renterd, which will hopefully fix this issues. Until then, the wallet balance is the better option for tax reporting, while the accounting information gives a good relativ overview over revenues over time and catergory.

## **Configuration template**

The basic configuration information can be found [here](../config_basics.md).

```yaml
name: "my_siahost"  #unique name
check_interval: "*/15 * * * *"  #cron schedule expression
summary_interval: "0 0 * * *"  #cron schedule expression
list_interval: "0 0 * * *"  #cron schedule expression
accounting_interval: "0 0 * * MON"  #optional, cron schedule expression
price_interval: "0 0 1 * *"  #cron schedule expression
alert_mute_interval: 24  #hours
host: "127.0.0.1::9980"
password: "abc123"
database: "~/myDb.sqlite"
csv_export: "~/myCsv.csv"  #optional
currency: "usd"  #supported: eur,usd
minimum_available_balance: 1000
autoprice:  #optional
    contract: 0.5  #siacoin
    storage: 1.0  #fiat/ month/ terabyte
    storage_max: 150  #siacoin/ month/ terabyte
    collateral_factor: 2.0
    upload: 1.0  #fiat/ terabyte
    upload_max: 150  #siacoin/ terabyte
    download: 2.0  #fiat/ terabyte
    download_max: 300  #siacoin/ terabyte
    sector_access: 0.0000018  #siacoin
    base_rpc: 0.00000012  #siacoin
```

## **Basic setup**

The plugin needs to store several data from the sia host and the blockchain in its own database. The path of the file is set by the key **database**.

Finally, the desired fiat currency has to be set by the key **currency**. The currencies `eur` and `usd` are supported.

## **Connect siad**

Communication with the siad instance is done via its API. The corresponding settings are passed to siad using the `--api-addr` parameter on startup. If this plugin is running on another machine of the local network, the address must be set to `0.0.0.0`. The key in the config for specifying the host is **host**.

Some API calls used by this plugin require a API password, set by the key **password**. The API password can usually be found here: `~/.sia/apipassword`.

## **Checks**

The plugin checks the health of the siad instance, including:

- sync status of the consensus
  - an alert is sent if the consensus is not synced
- wallet lock status
  - an alert is sent if the wallet is locked
- minimum balance (set by key **minimum_available_balance** in the configuration)
  - siad always needs some siacoins available to fulfill contracts, so ensure that not all of your balance gets locked
  - an alert is sent if the available balance gets below the treshold
- connection status
  - an alert is sent if siads connectabilty check failed or the host is not used by renters

The [execution interval](../config_basics.md) is set by the key **check_interval**.

## **Summary**

A summary is sent to the **info** channel and contains the following information:

- Sync status with height
- Balance
  - Total balance
  - Free balance
  - Locked collateral
  - Risked callateral
- Collateral reserve (more in the section below)
- Total storage usage
- Traffic
  - Download from renter since last summary
  - Upload to renter since last summary
  - not available if the siad instance was started after the last summary
- Number of contracts
  - Total
  - New contracts since last summary
  - Ended contracts since last summary
  - Failed proofs since last summary
- Settled earnings since last summary
- Non-settled balance in actice contracts
- Total earnings in active contracts since last summary

The _collateral reserve_ is a simple forecast how many percent of the available balance will not be locked if storage usage hits 100%. The calculation is really simple, so the results are not too accurate (especially if the configured collateral changes often). But it gives a quite good overview whether there is a risk of running out of available balance. A positive _collateral reserve_ means that there will be still some balance available when the whole storage is filled; a negative value means that the host will be running out of available balance to be locked as collateral before its storage gets full.

Furthermore, a list of all active contracts is written to the **debug** channel.

The [execution interval](../config_basics.md) is set by the key **summary_interval**.

## **List**

A summary is sent to the **report** channel, containing the following information:
- Coin price
- Balance
  - Total balance
  - Free balance
  - Locked collateral
  - Risked callateral

If the key **csv_export** is set, the balances are also added to a CSV export file.

The [execution interval](../config_basics.md) is set by the key **list_interval**.

## **Accounting**

The accounting feature gives an overview over the daily income. When triggered, it writes a table to the **report** channel with a row for each day since the last accounting report contain the following information:

- First height of the day
- Number of ended contracts
- Storage revenue
- Upload/ download revenue (excluding ephemeral accounts)
- Ephemeral account revenue
- Total revenue
- Coinprice
- Revenue in fiat

The data is taken from the contract list, so some other revenues (e.g. registry) is missing. But these revenues should represent only a small minority of total revenues.

The [execution interval](../config_basics.md) is set by the key **accounting_interval**.

## **Autoprice**

The fiat price of siacoin is set by supply and demand, so it is quite volatile. Host operators, however, usually do their cost calculations in fiat. So they need to update their prices from time to time.

The siahost plugin can automate this process with its autoprice feature. If the key **autoprice** is set in the configuration, this feature is active. Do not triffer price updates too often, since it interrupts traffic with the renters until they have the new price list. Once a week or less is fine.

When triggered (configured by key **price_interval**), its get the siacoin fiat price from the internet, calulates a new price table and updates the price tabele in siad. An upper limit in siacoin can be set, since some renters have hard limits for some prices. The collateral is also updated, since it is usually a multiple of the storage price.

The storage price is configured by the key **storage**, but the calculated price in siacoin will never exceed the value of the key **storage_max**.

The collateral is set to the storage price multiplied by the value of the key **collateral_factor**.

The upload (to renter) price is configured by the key **upload**, but the calculated price in siacoin will never exceed the value of the key **upload_max**.

The download (from renter) price is configured by the key **download**, but the calculated price in siacoin will never exceed the value of the key **download_max**.

The prices for contract formation, sector access and rpc are configured by the keys **contract**, **sector_access** and **base_rpc**. The are not calculated from fiat prices, since they only make a very small part of the income and the risk to get ignored by renters because of too high prices here is quite high.
