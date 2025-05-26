import praw
import os
import time
import logging
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Set up logging
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    filename="logs/bot.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# Authenticate Reddit client
reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_SECRET"),
    username=os.getenv("REDDIT_USERNAME"),
    password=os.getenv("REDDIT_PASSWORD"),
    user_agent=os.getenv("REDDIT_USER_AGENT")
)

# Subreddits to monitor
SUBREDDITS = ["AskReddit", "Kenya", "technology"]
COMMENT_TEXT = "All gas, no brakes! 🚀 [I'm a bot in development by u/No_Court_5398]"

# Memory to avoid replying multiple times
commented_ids = set()

def process_subreddit(subreddit_name):
    logging.info(f"Monitoring r/{subreddit_name}")
    subreddit = reddit.subreddit(subreddit_name)
    
    try:
        for post in subreddit.new(limit=6):
            if post.id not in commented_ids and not post.stickied:
                logging.info(f"Replying to: {post.title} ({post.id})")
                post.reply(COMMENT_TEXT)
                commented_ids.add(post.id)
                time.sleep(20)  # Sleep to avoid rate limit
    except Exception as e:
        logging.error(f"Error processing r/{subreddit_name}: {str(e)}")

def main_loop():
    while True:
        for sub in SUBREDDITS:
            process_subreddit(sub)
        logging.info("Cycle complete. Sleeping for 5 minutes...")
        time.sleep(300)  # 5 minutes

if __name__ == "__main__":
    logging.info("🚀 Bot starting up: All Gas No Brakes")
    main_loop()
