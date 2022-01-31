# Hourly Keke Pics

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

Source code of the [Hourly Keke Pics Twitter bot](https://twitter.com/HourlyKekePics) written in Python.

## Requirements

- Python 3.10 or later
- [`schedule`](https://pypi.python.org/pypi/schedule) and [`tweepy`](https://pypi.python.org/pypi/tweepy) libraries, run `pip install -r requirements.txt` to install them automatically.

## Setup and usage

Before running the bot, copy [`config_example.json`](./config_example.json) as `config.json`, then enter your API consumer keys as shown in your Twitter app's settings.

To start, run `python hourlykeke.py`.

When you start it up for the first time, follow the instructions on screen to authorize your bot account and get its access keys. Remember to save those keys in `config.json`, otherwise the bot will ask you for authorization every time you start it.

To exit out of the bot, just press <kbd>Ctrl</kbd>+<kbd>C</kbd>.

## Special thanks to&hellip;

- [@iqqydesu](https://twitter.com/iqqydesu) for coming up with the idea for this bot and providing some 200+ pics of Keke Tang, this bot wouldn't exist without their support!

---

Copyright 2022 PlayerOneTimmy ([@p1timmy](https://twitter.com/p1timmy)). Some rights reserved, released under the MIT License.
