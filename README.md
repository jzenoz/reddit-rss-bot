# RSS Feed -> Reddit Bot

A stateless Python bot that monitors a specified RSS Feed and automatically posts new articles to a specified Subreddit.

The bot posts as a specific Reddit User and automatically **distinguishes** the post (Green [M] badge) to indicate it is an official feed.

## Features

  * **RSS Monitoring:** Polls the feed every `POLLING_INTERVAL_MINUTES` minutes.
  * **Hybrid Duplicate Detection:** Uses a robust 3-layer system to prevent reposts:
    1.  **Memory Cache:** Remembers posts made during the current session to save API calls.
    2.  **Recent Feed (`.new`):** Checks the last 100 posts for immediate consistency (prevents reposting during search indexing lag).
    3.  **Deep Search (`.search`):** Queries full subreddit history to prevent reposting old items after long bot downtimes.
  * **Mod Actions:** Automatically distinguishes posts (requires Mod permissions).
  * **Safety/Debug Mode:** Includes a `REDDIT_DEBUG` flag that switches the bot to Read-Only mode and prints authentication scopes without posting.
  * **Secure:** Uses Reddit **Refresh Tokens** to avoid storing account passwords.

## Prerequisites

  * **Docker** and **Docker Compose**.
  * A Reddit account with **Moderator** status on the target subreddit.
  * **API Credentials:** A generic "Script" app created in Reddit preferences.

## Configuration (Environment Variables)

Copy .env.example to .env and fill in your real credentials. **Do not commit this file to version control.**

| Variable | Description | Example |
| :--- | :--- | :--- |
| `MONITORED_DOMAIN` | The domain to monitor (without `https://`) | `example.com` |
| `REDDIT_CLIENT_ID` | From Reddit App Preferences | `k8s7d6f...` |
| `REDDIT_CLIENT_SECRET` | From Reddit App Preferences | `so87s6d...` |
| `REDDIT_REFRESH_TOKEN` | Long-lived token (see below) | `8798798...` |
| `TARGET_SUBREDDIT` | The subreddit to post to | `YourSubreddit` |
| `POLLING_INTERVAL_MINUTES` | How often (in minutes) to check the RSS feed | `15` |
| `REDDIT_DEBUG` | If `True`, enables verbose logs and **disables posting** | `False` |

## Setup & Deployment

### 1\. Project Structure

```text
/opt/reddit-bot/
├── docker-compose.yml
├── .env
├── requirements.txt
└── bot_script/
    └── main.py
```

### 2\. How to Generate a Refresh Token

You need to run a one-time helper script or command to get the refresh token. The bot requires the following scopes:
`identity`, `submit`, `read`, `modposts`

You can generate the authorization URL using this Python snippet locally:

```python
import praw
reddit = praw.Reddit(
    client_id="YOUR_CLIENT_ID",
    client_secret="YOUR_CLIENT_SECRET",
    redirect_uri="http://localhost:8080",
    user_agent="TokenGen/1.0"
)
print(reddit.auth.url(scopes=["identity", "modposts", "submit", "read"], state="init", duration="permanent"))
```

### 3\. Local Development

It is recommended to use a virtual environment for local development.

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4\. Docker Compose

Save the following as `docker-compose.yml`:

```yaml
version: '3.8'

services:
  reddit-bot:
    image: python:3.9-slim
    container_name: reddit-rss-bot
    restart: unless-stopped
    volumes:
      - ./bot_script:/app
    working_dir: /app
    env_file:
      - .env
    # Installs dependencies and runs python in unbuffered mode (-u)
    command: >
      sh -c "pip install -r requirements.txt && python -u main.py"
```

### 5\. Running the Bot

Start the container in the background:

```bash
docker-compose up -d
```

View logs to ensure it is running:

```bash
docker logs -f reddit-rss-bot
```

## Debugging

To test the bot without actually posting to Reddit:

1.  Set `REDDIT_DEBUG=True` in your `.env` file.
2.  Restart the container: `docker-compose restart reddit-rss-bot`.
3.  Check the logs. The bot will:
      * Print the current authenticated scopes.
      * Set the PRAW instance to `read_only`.
      * Print the URLs it is checking against.
      * Print the title/URL it *would* have posted.
