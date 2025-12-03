#!/usr/bin/env python3
import os
import sys
import time

import feedparser
import praw
import schedule
from loguru import logger

# --- CONFIGURATION ---
MONITORED_DOMAIN = os.getenv("MONITORED_DOMAIN")
RSS_URL = f"https://{MONITORED_DOMAIN}/blog/rss"
TARGET_SUBREDDIT = os.getenv("TARGET_SUBREDDIT")
POLLING_INTERVAL_MINUTES = int(os.getenv("POLLING_INTERVAL_MINUTES", 15))
DEBUG = os.getenv("REDDIT_DEBUG", "False").lower() == "true"

# Default loguru logger level is DEBUG
if not DEBUG:
    logger.remove()
    logger.add(sys.stderr, level="INFO")


def get_reddit_instance():
    try:
        return praw.Reddit(
            client_id=os.getenv("REDDIT_CLIENT_ID"),
            client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
            refresh_token=os.getenv("REDDIT_REFRESH_TOKEN"),
            user_agent=f"{MONITORED_DOMAIN}Bot/1.0",
        )
    except Exception as e:
        logger.error(f"Error initializing Reddit: {e}")
        return None


def is_already_posted(reddit, url_to_check):
    try:
        search_results = list(reddit.subreddit(TARGET_SUBREDDIT).search(query=f"site:{MONITORED_DOMAIN}", sort="new"))

        logger.debug(f"Retrieved {len(search_results)} entries")

        for submission in search_results:
            logger.debug(f"Checking submission:\n{submission.url} {submission.title}")
            if submission.url.rstrip("/") == url_to_check.rstrip("/"):
                return True
    except Exception as e:
        logger.error(f"Error checking subreddit history: {e}")
        sys.exit(1)
    return False


def run_bot():
    logger.info("Checking feed...")

    if not MONITORED_DOMAIN or not TARGET_SUBREDDIT:
        logger.error("MONITORED_DOMAIN and TARGET_SUBREDDIT must be set in the environment.")
        sys.exit(1)

    # Parse RSS Feed
    try:
        logger.debug(f"Feed URL: {RSS_URL}")
        feed = feedparser.parse(RSS_URL)
        if not feed.entries:
            logger.info("Feed is empty or unreachable.")
            return
    except Exception as e:
        logger.error(f"Error parsing feed: {e}")
        return

    latest_entry = feed.entries[0]
    latest_link = latest_entry.link

    # Check Reddit directly
    reddit = get_reddit_instance()

    if not reddit:
        return

    logger.debug(f"List of authenticated scopes for user {reddit.user.me()}: {reddit.auth.scopes()}")
    if DEBUG:
        logger.debug("Setting read-only mode due to REDDIT_DEBUG set to True")
        reddit.read_only = True

    if is_already_posted(reddit, latest_link):
        logger.info(f"Skipping: '{latest_entry.title}' (Already on Reddit)")
    else:
        logger.info(f"New post found: {latest_entry.title}")
        try:
            # Submit
            subreddit = reddit.subreddit(TARGET_SUBREDDIT)
            submission = subreddit.submit(title=latest_entry.title, url=latest_link)
            logger.info(f"Posted: {submission.shortlink}")

            # Mod Distinguish (Green [M]) - No Sticky
            try:
                submission.mod.distinguish(how="yes", sticky=False)
                logger.info("Successfully distinguished as Mod.")
            except Exception as e:
                logger.warning(f"Could not distinguish post: {e}")

        except Exception as e:
            logger.critical(f"Critical Error posting to Reddit: {e}")
            logger.debug(f"Content:\nTitle:{latest_entry.title}\nURL:{latest_link}")


if __name__ == "__main__":
    # Check immediately
    run_bot()

    # Then check every POLLING_INTERVAL_MINUTES minutes
    schedule.every(POLLING_INTERVAL_MINUTES).minutes.do(run_bot)

    logger.info("Bot Service Started...")
    while True:
        schedule.run_pending()
        time.sleep(15)
