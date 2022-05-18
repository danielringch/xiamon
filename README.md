# chiatools
Tools for running chia farmers and full nodes on linux systems like Raspberry Pi.

Dependecies:
pytz_deprecation_shim
croniter
discord.py
ciso8601

How to enable smart support:

- as root, copy the smartctl binary (usually in /usr/sbin) to a directory of your choise
- as root, make it executable for the user running chiamon using the command 'chmod u+s smartctl'
- add the path to the smartctl binary to your config