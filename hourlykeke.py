#!/usr/bin/env python3

import json
import logging
import os
import random
import socket
import time
from collections import deque

import schedule
import tweepy

__version__ = "1.2.1"
LOG_LEVEL = logging.INFO
LOGFILE_LEVEL = logging.DEBUG
# Same pic can't be sent more than once within this many hours
RECENTS_COUNT = 12
LOG_FMT = "%(levelname)s (%(name)s): %(message)s"

# File and directory names
CONFIG_FILE = "config.json"
IMG_DIR = "img"
LOGFILE = "bot.log"
RECENTS_LIST_FILE = "recentpics.txt"

logger = logging.getLogger(__name__)
config_dict = {}


class ImageQueue():
    def __init__(self):
        self.items = []

    def enqueue(self, filename: str):
        self.items.insert(0, filename)

    def dequeue(self) -> str:
        return self.items.pop()

    def __len__(self):
        return self.items.__len__()

    def __str__(self):
        return self.items.__str__()

    def is_empty(self) -> bool:
        return self.__len__() < 1

    def first(self) -> str:
        if not len(self.items):
            raise IndexError("queue is empty")
        return self.items[-1]


class TwitterClient():
    def __init__(self, keys: dict):
        auth = tweepy.OAuth1UserHandler(
            keys["consumer"], keys["consumer_secret"], callback="oob"
        )
        if keys["access"] == "" and keys["access_secret"] == "":
            print(
                "\nOpen the following link in your browser:\n"
                f"{auth.get_authorization_url()}"
            )
            pin = input("and enter the PIN on that page: ").strip()
            while len(pin) != 6 and not pin.isdigit():
                pin = input("Invalid input, enter PIN: ").strip()
            keys["access"], keys["access_secret"] = auth.get_access_token(pin)
            print(
                "Here are your access token and secret keys:\n"
                f'{keys["access"]}\n{keys["access_secret"]}\n\n'
                "To skip this step next time, copy the above keys to your\n"
                "config.json file. Press Enter/Return to continue...", end=""
            )
            input()
        auth.set_access_token(keys["access"], keys["access_secret"])

        self._api = tweepy.API(auth)
        self._authenticate()

    def _authenticate(self):
        self.user = self._api.verify_credentials().screen_name
        logger.info(
            "Twitter API keys verified, authenticated as @%s",
            self.user)

    def send_tweet(self, media_path: str, tweet=""):
        try:
            logger.debug("Uploading %s", media_path)
            media_id = self._api.media_upload(media_path).media_id_string
            logger.debug("Sending tweet")
            response = self._api.update_status(status=tweet, media_ids=[media_id])
            return response
        except socket.gaierror:
            # Retry if tweet didn't send due to network-related issues
            logger.error("Failed to send tweet, retrying in 30 seconds")
            time.sleep(30)
            return self.send_tweet(media_path, tweet)
        except tweepy.TweepyException:
            logger.exception("Failed to send tweet")


image_queue = ImageQueue()
recent_files = deque([], RECENTS_COUNT)


def parse_config():
    global config_dict
    with open(CONFIG_FILE) as f:
        config_dict = json.load(f)
    verify_keys()


def verify_keys():
    keys = config_dict["twitter_keys"]
    for k in ("consumer", "consumer_secret", "access", "access_secret"):
        assert k in keys, \
            f'Required key "{k}" not found in config file'
        assert isinstance(keys[k], str), \
            f'Required key "{k}" must have value of type string '
        if k.startswith("consumer"):
            assert keys[k] != "", f'Required key "{k}" can\'t be blank'


def populate_queue():
    files = os.listdir(IMG_DIR)
    counter = 0
    while len(image_queue) < RECENTS_COUNT:
        filename = random.choice(files)
        ext = filename.split(".", -1)[-1]
        if ext.lower() not in ("jpg", "jpeg", "png", "gif"):
            continue
        path = f"{IMG_DIR}/{filename}"
        if path in recent_files or path in image_queue.items:
            continue
        image_queue.enqueue(path)
        counter += 1
    logger.info(f"Added {counter} image{'s' if counter != 1 else ''} to queue")


def tweet_image(bot: TwitterClient, no_delay: bool = False):
    # Step 1: Repopulate queue if empty
    if len(image_queue) < 1:
        populate_queue()

    # Step 2: Pull out next image on front of queue
    filename = image_queue.dequeue()
    while not os.path.isfile(filename):
        filename = image_queue.dequeue()

    # Step 3: Send tweet and add filename to recents list
    if not no_delay:
        time.sleep(random.randrange(1, 30))

    response = bot.send_tweet(filename)
    if response:
        logger.info(
            "Tweet sent, view it at "
            f"https://twitter.com/{bot.user}/status/{response.id}"
        )
        q_len = len(image_queue)
        logger.debug(f"{q_len} image{'s' if q_len != 1 else ''} remaining in queue")

        # Save recent images file
        recent_files.append(filename)
        save_recent_filenames()
    else:
        logger.info(
            f"Tweet for {filename} will be sent at next scheduled interval"
        )


def set_up_logging():
    logger.setLevel(LOGFILE_LEVEL)
    logging.Formatter.converter = time.gmtime
    fmt = logging.Formatter("[%(asctime)s] " + LOG_FMT, "%Y-%m-%dT%H:%M:%SZ")

    # Create console handler
    clihandler = logging.StreamHandler()
    clihandler.setLevel(LOG_LEVEL)
    clihandler.setFormatter(fmt)
    logger.addHandler(clihandler)

    # Create file handler
    filehandler = logging.FileHandler(LOGFILE)
    filehandler.setFormatter(fmt)
    logger.addHandler(filehandler)

    # Silence info/debug logs from libraries
    logging.getLogger("oauthlib").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("requests_oauthlib").setLevel(logging.WARNING)
    logging.getLogger("schedule").setLevel(logging.WARNING)
    logging.getLogger("tweepy").setLevel(logging.WARNING)


def load_recent_pics():
    if RECENTS_LIST_FILE not in os.listdir():
        logger.debug(
            f"{RECENTS_LIST_FILE} not found in current directory"
        )
        return

    with open(RECENTS_LIST_FILE) as f:
        count = 0
        for line in f:
            line = line.strip("\n")
            if line:
                recent_files.append(line)
            count += 1
        logger.debug(
            f"Found {count} filename{'s' if count != 1 else ''} in recents file"
        )
        logger.info("Recent filenames loaded")


def save_recent_filenames():
    with open(RECENTS_LIST_FILE, mode="w") as f:
        f.write("\n".join(recent_files) + "\n")
    logger.debug(
        f"Saved paths of last {RECENTS_COUNT} images to {RECENTS_LIST_FILE}"
    )


def main(minute: int = 5):
    assert 60 > minute >= 0, "minute must be between 0 and 59"

    # Exit if no images are found or directory is missing
    if IMG_DIR not in os.listdir():
        raise IOError("image directory not found, create it and try again")
    if not os.listdir(IMG_DIR):
        raise IOError("image directory is empty, add images to it and try again")

    # Set up Twitter API client
    bot = TwitterClient(config_dict["twitter_keys"])

    # Post immediately if current minute is equal to target minute
    current_min = time.localtime().tm_min
    if current_min == minute:
        tweet_image(bot, True)

    # Set up schedule
    schedule.every().hour.at(f":{minute:02d}").do(tweet_image, bot, False)
    next_run = schedule.next_run().strftime('%H:%M:%S')
    logger.info(
        f"Schedule set to {minute} minute{'s' if minute != 1 else ''} "
        f"past the hour, next tweet to be sent at {next_run}"
    )

    # Main loop
    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    set_up_logging()
    logger.info(f"Hourly Keke Pics v{__version__} is starting up...")

    try:
        load_recent_pics()
        parse_config()
        main(5)
    except (KeyboardInterrupt, SystemExit):
        # Use Ctrl-C to terminate the bot
        logger.info("Shutting down...")
    except AssertionError as e:
        logger.error(e)
    except Exception:
        logger.exception("Fatal error occurred, shutting down...")

    schedule.clear()
