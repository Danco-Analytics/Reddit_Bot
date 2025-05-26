import praw
import google.generativeai as genai
import time
import os
import random
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from dotenv import load_dotenv

# Load environment variables from .env file
# Ensure this script is in the same directory as your .env file
load_dotenv()

# --- Configuration from Environment Variables ---
REDDIT_APP_CLIENT_ID = os.getenv("REDDIT_APP_CLIENT_ID")
REDDIT_APP_CLIENT_SECRET = os.getenv("REDDIT_APP_CLIENT_SECRET")
REDDIT_APP_USER_AGENT = os.getenv("REDDIT_APP_USER_AGENT")

REDDIT_BOT_USERNAME = os.getenv("REDDIT_BOT_USERNAME") # For the account the bot posts AS
REDDIT_BOT_PASSWORD = os.getenv("REDDIT_BOT_PASSWORD") # Password for the bot's account

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# Get Gemini model name from .env, defaulting if not specified
# You can change the default here or ensure GEMINI_MODEL_NAME is always in your .env
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-1.0-pro")


# --- Static Bot Settings ---
TARGET_SUBREDDITS = ["learnpython", "AskReddit", "testingground4bots", "BotTown", "jokes", "puns"]
REPLY_INTERVAL_SECONDS = 15 * 60
PROCESSED_ITEMS_FILE = "processed_items_gemini.txt"
BOT_DISCLAIMER = "\n\n---\n\n*I'm All_Gas_No_Brakes, an AI bot with a penchant for puns and a byte of dark humor. This reply was auto-generated with Gemini.*"
LOG_FILE = "bot_activity_log.txt"

# --- Logging Function ---
def log_message(message):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    full_log = f"[{timestamp}] {message}"
    print(full_log) # Also print to console (visible in screen/tmux)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(full_log + "\n")
    except Exception as e:
        print(f"Error writing to log file: {e}")

# --- Sentiment Analysis Setup ---
sid = None
try:
    sid = SentimentIntensityAnalyzer()
    log_message("SentimentIntensityAnalyzer loaded successfully.")
except LookupError:
    log_message("VADER lexicon not found. Please ensure NLTK data (vader_lexicon, punkt) is downloaded in the correct Python environment.")
except Exception as e:
    log_message(f"Error loading SentimentIntensityAnalyzer: {e}")

# --- Initialize Gemini ---
gemini_model = None
try:
    if GEMINI_API_KEY and "YOUR_GEMINI_API_KEY" not in GEMINI_API_KEY and "AIzaSyC" in GEMINI_API_KEY : # Basic check for placeholder
        genai.configure(api_key=GEMINI_API_KEY)
        log_message(f"Configuring Gemini with model: {GEMINI_MODEL_NAME}")
        gemini_model = genai.GenerativeModel(GEMINI_MODEL_NAME)
        # To confirm model validity early, you could make a small, non-essential call here,
        # but it will also become apparent on the first actual generation attempt.
        log_message(f"Gemini API configured successfully with model {GEMINI_MODEL_NAME}.")
    else:
        log_message("Gemini API key is missing, a placeholder, or seems invalid. Please check .env file.")
except Exception as e:
    log_message(f"Error configuring Gemini API or model {GEMINI_MODEL_NAME}: {e}")
    log_message("Please ensure the GEMINI_MODEL_NAME in your .env file is correct, supported, and you have access to it.")

# --- Helper Functions ---
def load_processed_items():
    if not os.path.exists(PROCESSED_ITEMS_FILE):
        return set()
    try:
        with open(PROCESSED_ITEMS_FILE, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f)
    except Exception as e:
        log_message(f"Error loading processed items file: {e}")
        return set()

def save_processed_item(item_id):
    try:
        with open(PROCESSED_ITEMS_FILE, "a", encoding="utf-8") as f:
            f.write(item_id + "\n")
    except Exception as e:
        log_message(f"Error saving processed item ID {item_id}: {e}")

def get_sentiment_score(text):
    if not sid:
        return 0 
    return sid.polarity_scores(text)['compound']

def generate_gemini_reply(text_to_reply_to, context_title=""):
    if not gemini_model:
        return "My circuits are a bit tangled right now, can't generate a response." # Should be caught by initial checks
    prompt = f"""You are a Reddit bot persona: witty, casual, a genius, and a pun master.
    You have a taste for dark humor but know how to keep it clever and not overly offensive or explicit, respecting general content guidelines.
    Your goal is to generate an engaging comment related to the provided text.
    Adapt your humor and style slightly based on the topic apparent from the text. If it's serious, be more witty/insightful than outright dark. If it's lighthearted, unleash the puns.

    Context (e.g., Post Title, if available): "{context_title}"
    Text to reply to: "{text_to_reply_to}"

    Generate a relevant, witty, and engaging comment. Employ puns or clever dark humor where appropriate and not jarring.
    Keep the comment concise, like a typical good Reddit comment.
    """
    try:
        log_message(f"Generating Gemini reply using {GEMINI_MODEL_NAME} for: \"{text_to_reply_to[:60].replace(os.linesep, ' ')}...\"")
        response = gemini_model.generate_content(prompt)
        if hasattr(response, 'text') and response.text:
            return response.text.strip()
        elif response.parts:
             return "".join(part.text for part in response.parts).strip()
        else:
            log_message(f"Gemini API response (model {GEMINI_MODEL_NAME}) did not contain text or parts.")
            if hasattr(response, 'candidates') and response.candidates and response.candidates[0].finish_reason != 'STOP':
                log_message(f"Gemini generation stopped due to: {response.candidates[0].finish_reason}")
                if response.candidates[0].safety_ratings:
                    log_message(f"Safety Ratings: {response.candidates[0].safety_ratings}")
            return "My pun generator just blue-screened. Try again later!"
    except Exception as e:
        log_message(f"Error calling Gemini API with model {GEMINI_MODEL_NAME}: {e}")
        return "My AI brain just short-circuited. I'll be back!"

# --- Main Bot Logic ---
def run_bot():
    # Initial checks for essential configurations
    essential_configs = {
        "REDDIT_APP_CLIENT_ID": REDDIT_APP_CLIENT_ID,
        "REDDIT_APP_CLIENT_SECRET": REDDIT_APP_CLIENT_SECRET,
        "REDDIT_APP_USER_AGENT": REDDIT_APP_USER_AGENT,
        "REDDIT_BOT_USERNAME": REDDIT_BOT_USERNAME,
        "REDDIT_BOT_PASSWORD": REDDIT_BOT_PASSWORD,
        "GEMINI_API_KEY": GEMINI_API_KEY,
        "GEMINI_MODEL_NAME": GEMINI_MODEL_NAME
    }
    for config_name, config_value in essential_configs.items():
        if not config_value or "YOUR_" in config_value.upper() or config_value == "placeholder_value": # Add more placeholder checks if needed
            log_message(f"CRITICAL ERROR: Configuration for '{config_name}' is missing, a placeholder, or invalid in .env file.")
            return
            
    if not sid:
        log_message("CRITICAL ERROR: Sentiment analyzer (VADER) failed to load. Ensure NLTK data is downloaded.")
        return
    if not gemini_model: 
        log_message("CRITICAL ERROR: Gemini model failed to initialize. Check API key, model name in .env, internet, and previous logs.")
        return

    log_message("Initializing Reddit instance...")
    try:
        reddit = praw.Reddit(
            client_id=REDDIT_APP_CLIENT_ID,
            client_secret=REDDIT_APP_CLIENT_SECRET,
            user_agent=REDDIT_APP_USER_AGENT,
            username=REDDIT_BOT_USERNAME,
            password=REDDIT_BOT_PASSWORD
        )
        me = reddit.user.me()
        # Check if login was successful and if the logged-in user matches the expected bot username
        if me is None or me.name.lower() != REDDIT_BOT_USERNAME.lower():
            actual_user = me.name if me else "None"
            log_message(f"CRITICAL ERROR: Failed to log in to Reddit as the expected bot user '{REDDIT_BOT_USERNAME}'. Logged in as '{actual_user}'. Check REDDIT_BOT_USERNAME and REDDIT_BOT_PASSWORD in .env file and the bot account's status on Reddit.")
            return
        log_message(f"Successfully logged in to Reddit as: {me.name}")
    except Exception as e:
        log_message(f"CRITICAL ERROR: Failed to log in to Reddit: {e} (Type: {type(e).__name__})")
        return

    processed_items = load_processed_items()
    log_message(f"Loaded {len(processed_items)} processed item IDs.")

    while True:
        try:
            current_time_str = time.strftime("%Y-%m-%d %H:%M:%S")
            log_message(f"--- Starting new scan cycle at {current_time_str} ---")
            subreddit_name = random.choice(TARGET_SUBREDDITS)
            log_message(f"Scanning subreddit: r/{subreddit_name}")
            subreddit = reddit.subreddit(subreddit_name)
            
            replied_in_cycle = False

            for post in subreddit.hot(limit=15): # Get some hot posts
                if post.id in processed_items or post.stickied:
                    continue
                if post.author and post.author.name.lower() == REDDIT_BOT_USERNAME.lower():
                    continue
                if post.archived or post.locked:
                    continue

                post_content_for_sentiment = post.title + " " + post.selftext
                sentiment = get_sentiment_score(post_content_for_sentiment)
                log_message(f"Post '{post.title[:30].replace(os.linesep, ' ')}...' (ID: {post.id}) sentiment: {sentiment:.2f}")

                if sentiment < -0.2: # Avoid very negative posts
                    log_message(f"Skipping post {post.id} due to negative sentiment ({sentiment:.2f}).")
                    save_processed_item(post.id)
                    continue
                
                post.comments.replace_more(limit=0) # Load top-level comments
                comments_to_consider = [
                    c for c in post.comments.list()[:20] # Look at more comments
                    if c.author and c.author.name.lower() != REDDIT_BOT_USERNAME.lower() and c.id not in processed_items and not c.stickied
                ]

                if not comments_to_consider:
                    continue # Try next post if no suitable comments on this one
                
                target_comment = random.choice(comments_to_consider)
                log_message(f"Selected comment (ID: {target_comment.id}) by u/{target_comment.author.name if target_comment.author else '[deleted]'} under post '{post.title[:30].replace(os.linesep, ' ')}...'")

                try:
                    log_message(f"Upvoting comment ID {target_comment.id}")
                    target_comment.upvote()
                except Exception as e:
                    log_message(f"Failed to upvote comment {target_comment.id}: {e}")

                reply_text_base = generate_gemini_reply(target_comment.body, context_title=post.title)
                
                if reply_text_base and "unable to generate" not in reply_text_base and "lost it" not in reply_text_base and "short-circuited" not in reply_text_base:
                    full_reply_text = reply_text_base + BOT_DISCLAIMER
                    log_message(f"Attempting to reply to comment {target_comment.id}: \"{full_reply_text[:100].replace(BOT_DISCLAIMER, '').replace(os.linesep, ' ')}...\"")
                    try:
                        target_comment.reply(full_reply_text)
                        log_message(f"Successfully replied to comment ID {target_comment.id} in r/{subreddit_name}")
                        save_processed_item(target_comment.id)
                        processed_items.add(target_comment.id)
                        replied_in_cycle = True
                        time.sleep(10) # Pause after successful reply
                        break # Break from posts loop after one reply in cycle to wait for main interval
                    except praw.exceptions.APIException as e:
                        log_message(f"Reddit API Exception while replying to comment {target_comment.id}: {e}")
                        if "RATELIMIT" in str(e).upper():
                            log_message("Rate limit hit. Sleeping for 5 minutes.")
                            time.sleep(300) # Sleep longer if rate limited
                        elif any(err_str in str(e).upper() for err_str in ["DELETED_COMMENT", "TOO_OLD", "THREAD_LOCKED", "COMMENT_DELETED", "NOT_AUTHOR", "PARENT_DELETED"]):
                            log_message(f"Comment/Post issue for {target_comment.id}. Marking comment as processed.")
                            save_processed_item(target_comment.id)
                        else: # Other API errors
                            log_message(f"Unhandled API exception for {target_comment.id}. Marking as processed to avoid loop on error.")
                            save_processed_item(target_comment.id)
                    except Exception as e:
                        log_message(f"An unexpected error occurred while replying to comment {target_comment.id}: {e}")
                        save_processed_item(target_comment.id) # Mark as processed to avoid retrying faulty comment
                else:
                    log_message(f"Gemini (model {GEMINI_MODEL_NAME}) did not generate a suitable reply for comment {target_comment.id}.")
                    save_processed_item(target_comment.id) # Mark as processed if AI fails
                
                time.sleep(random.uniform(2,5)) # Small random delay between checking comments/posts if no reply was made

            if not replied_in_cycle:
                log_message("No new suitable posts/comments found to reply to in this cycle across scanned posts.")

            log_message(f"--- Cycle finished. Waiting for {REPLY_INTERVAL_SECONDS // 60} minutes ({REPLY_INTERVAL_SECONDS}s) before next scan. ---")
            time.sleep(REPLY_INTERVAL_SECONDS)

        except praw.exceptions.PRAWException as e: # More general PRAW errors
            log_message(f"A PRAW specific error occurred in the main loop: {e}")
            log_message("Sleeping for 60 seconds before retrying...")
            time.sleep(60)
        except KeyboardInterrupt:
            log_message("KeyboardInterrupt received. Shutting down bot...")
            break # Exit the while True loop
        except Exception as e:
            log_message(f"An critical unexpected error occurred in the main loop: {e} (Type: {type(e).__name__})")
            log_message("This could be a network issue, an unhandled API change, or a bug.")
            log_message("Sleeping for 5 minutes before retrying the loop...")
            time.sleep(300) # Sleep longer for major unknown issues

if __name__ == "__main__":
    log_message("Starting Reddit Bot All_Gas_No_Brakes (dotenv version)...")
    # Initial configuration checks are now more robust and happen at the start of run_bot()
    run_bot()
    log_message("Bot script finished or exited.")