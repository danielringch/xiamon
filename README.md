# chiatools
Tools for running chia farmers and full nodes on linux systems like Raspberry Pi.

Dependecies:
colorama
pytz_deprecation_shim
croniter
discord.py
ciso8601
psutil
pyaml

How to enable smart support:

- as root, copy the smartctl binary (usually in /usr/sbin) to a directory of your choise
- as root, make it executable for the user running chiamon using the command 'chmod u+s smartctl'
- add the path to the smartctl binary to your config

Common smart attributes:
4: Start/Stop Count
5: Reallocated Sector Count
10: Spin Retry Count
190: Airflow Temperature
193: Load Cycle Count
194: Drive Temperature
197: Current Pending Sector Count