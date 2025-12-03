import importlib
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

from loguru import logger

# Add the bot_script directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "bot_script")))
import main

UNIT_TEST_DEBUG = False
if os.getenv("REDDIT_DEBUG", "False").lower() == "true":
    UNIT_TEST_DEBUG = True


class TestBot(unittest.TestCase):

    def setUp(self):
        os.environ["MONITORED_DOMAIN"] = "example.com"
        os.environ["TARGET_SUBREDDIT"] = "test_subreddit"
        os.environ["REDDIT_CLIENT_ID"] = "test_id"
        os.environ["REDDIT_CLIENT_SECRET"] = "test_secret"
        os.environ["REDDIT_REFRESH_TOKEN"] = "test_token"
        os.environ["REDDIT_DEBUG"] = "True"

        self.logs = []
        logger.add(self.logs.append)
        if UNIT_TEST_DEBUG:
            logger.add(sys.stderr)
        importlib.reload(main)

    def tearDown(self):
        logger.remove()

    @patch("main.praw.Reddit")
    def test_get_reddit_instance(self, mock_reddit):
        logger.info(f"Running test: {self._testMethodName}")
        # Call the function
        main.get_reddit_instance()

        # Assert that praw.Reddit was called with the correct parameters
        mock_reddit.assert_called_once_with(client_id="test_id", client_secret="test_secret", refresh_token="test_token", user_agent="example.comBot/1.0")

    @patch("main.praw.Reddit")
    def test_is_already_posted_true(self, mock_reddit):
        logger.info(f"Running test: {self._testMethodName}")
        # Create a mock submission
        mock_submission = MagicMock()
        mock_submission.url = "http://example.com/blog/post1"

        # Configure the mock reddit instance
        mock_reddit_instance = MagicMock()
        mock_reddit_instance.subreddit.return_value.search.return_value = [mock_submission]
        mock_reddit.return_value = mock_reddit_instance

        # Call the function
        result = main.is_already_posted(mock_reddit_instance, "http://example.com/blog/post1")

        # Assert that the function returns True
        self.assertTrue(result)

    @patch("main.praw.Reddit")
    def test_is_already_posted_false(self, mock_reddit):
        logger.info(f"Running test: {self._testMethodName}")
        # Configure the mock reddit instance
        mock_reddit_instance = MagicMock()
        mock_reddit_instance.subreddit.return_value.search.return_value = []
        mock_reddit.return_value = mock_reddit_instance

        # Call the function
        result = main.is_already_posted(mock_reddit_instance, "http://example.com/blog/post1")

        # Assert that the function returns False
        self.assertFalse(result)

    @patch("main.feedparser.parse")
    @patch("main.get_reddit_instance")
    def test_read_only_mode(self, mock_get_reddit_instance, mock_feedparser_parse):
        logger.info(f"Running test: {self._testMethodName}")
        # Create a mock feed
        mock_feed = MagicMock()
        mock_feed.entries[0].title = "Test Post"
        mock_feed.entries[0].link = "http://example.com/blog/post1"
        mock_feedparser_parse.return_value = mock_feed

        # Configure the mock reddit instance
        mock_reddit_instance = MagicMock()
        mock_reddit_instance.subreddit.return_value.search.return_value = []
        mock_get_reddit_instance.return_value = mock_reddit_instance
        mock_reddit_instance.subreddit.return_value.submit.return_value.shortlink = "https://redd.it/eorhm"

        # Call the function
        main.run_bot()

        self.assertTrue(mock_reddit_instance.read_only)

    @patch("main.feedparser.parse")
    @patch("main.get_reddit_instance")
    def test_run_bot_new_post(self, mock_get_reddit_instance, mock_feedparser_parse):
        logger.info(f"Running test: {self._testMethodName}")
        # Create a mock feed
        mock_feed = MagicMock()
        mock_feed.entries[0].title = "Test Post"
        mock_feed.entries[0].link = "http://example.com/blog/post1"
        mock_feedparser_parse.return_value = mock_feed

        # Configure the mock reddit instance
        mock_reddit_instance = MagicMock()
        mock_reddit_instance.subreddit.return_value.search.return_value = []
        mock_get_reddit_instance.return_value = mock_reddit_instance
        mock_reddit_instance.subreddit.return_value.submit.return_value.shortlink = "https://redd.it/eorhm"

        # Call the function
        main.run_bot()

        self.assertTrue(any("New post found: Test Post" in log for log in self.logs))
        self.assertTrue(any("Posted: https://redd.it/eorhm" in log for log in self.logs))

        # Assert that the post was submitted
        mock_reddit_instance.subreddit.return_value.submit.assert_called_once_with(title="Test Post", url="http://example.com/blog/post1")

    @patch("main.feedparser.parse")
    @patch("main.get_reddit_instance")
    def test_run_bot_already_posted(self, mock_get_reddit_instance, mock_feedparser_parse):
        logger.info(f"Running test: {self._testMethodName}")
        # Create a mock feed
        mock_feed = MagicMock()
        mock_feed.entries[0].title = "Test Post"
        mock_feed.entries[0].link = "http://example.com/blog/post1"

        mock_feedparser_parse.return_value = mock_feed

        # Create a mock submission
        mock_submission = MagicMock()
        mock_submission.url = "http://example.com/blog/post1"

        # Configure the mock reddit instance
        mock_reddit_instance = MagicMock()
        mock_reddit_instance.subreddit.return_value.search.return_value = [mock_submission]
        mock_get_reddit_instance.return_value = mock_reddit_instance

        # Call the function
        main.run_bot()

        self.assertTrue(any("Skipping: 'Test Post' (Already on Reddit)" in log for log in self.logs))

        # Assert that the post was not submitted
        mock_reddit_instance.subreddit.return_value.submit.assert_not_called()


if __name__ == "__main__":
    unittest.main()
