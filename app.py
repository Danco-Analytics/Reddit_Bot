import praw
import google.generativeai as genai
import time
import os
import random
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer

# --- Configuration ---
# !! CRITICAL: Ensure these are correct and SECURE !!
REDDIT_CLIENT_ID = "vEW0UrVrMw9rAc8VAtr_lg"
REDDIT_CLIENT_SECRET = "tyhSZUJ9fnFLhHh_SkPRfHKzmSom_g"
REDDIT_USER_AGENT = "All_Gas_No_Brakes_Bot v0.2 by u/No_Court_5398"
REDDIT_BOT_USERNAME = "All_Gas_No_Brakes_Bot_Account"  # <--- VERIFY/CHANGE THIS
REDDIT_BOT_PASSWORD = "YourBotAccountPassword_Must_Change"  # <--- YOU MUST CHANGE THIS TO THE REAL PASSWORD

GEMINI_API_KEY = "AIzaSyCOyiZkk8t7zFtX4zC9G4v66MPJfgjIi84" # <--- VERIFY/CHANGE THIS IF NEEDED

TARGET_SUBREDDITS = ["learnpython", "AskReddit", "testingground4bots", "BotTown", "jokes", "puns"]
REPLY_INTERVAL_SECONDS = 15 * 60
PROCESSED_ITEMS_FILE = "processed_items_gemini.txt"
BOT_DISCLAIMER = "\n\n---\n\n*I'm All_Gas_No_Brakes*"
LOG_FILE = "bot_activity_log.txt" # Added for logging

# --- Logging Function ---
def log_message(message):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    full_log = f"[{timestamp}] {message}"
    print(full_log) # Print to console (will be visible in screen session)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f: # Ensure utf-8 encoding
            f.write(full_log + "\n")
    except Exception as e:
        print(f"Error writing to log file: {e}")


# --- Sentiment Analysis Setup ---
sid = None
try:
    sid = SentimentIntensityAnalyzer()
    log_message("SentimentIntensityAnalyzer loaded successfully.")
except LookupError:
    log_message("VADER lexicon not found. On your server, run Python, then: import nltk; nltk.download('vader_lexicon'); nltk.download('punkt')")
    # Bot will exit if sid is None later, which is good.
except Exception as e:
    log_message(f"Error loading SentimentIntensityAnalyzer: {e}")


# --- Initialize Gemini ---
gemini_model = None
try:
    if GEMINI_API_KEY and "YOUR_GEMINI_API_KEY" not in GEMINI_API_KEY and "AIzaSyC" in GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
        gemini_model = genai.GenerativeModel('gemini-pro')
        log_message("Gemini API configured successfully.")
    else:
        log_message("Gemini API key seems to be a placeholder or invalid. Please check GEMINI_API_KEY.")
except Exception as e:
    log_message(f"Error configuring Gemini API: {e}")

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
        log_message("Sentiment analyzer not available. Cannot get score.")
        return 0 # Neutral default, but bot should ideally not proceed if sid failed.
    return sid.polarity_scores(text)['compound']

def generate_gemini_reply(text_to_reply_to, context_title=""):
    if not gemini_model:
        log_message("Gemini model not initialized. Cannot generate reply.")
        return "My circuits are a bit tangled right now, can't generate a response."

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
        log_message(f"Generating Gemini reply for: \"{text_to_reply_to[:60].replace(os.linesep, ' ')}...\"")
        response = gemini_model.generate_content(prompt)
        if hasattr(response, 'text') and response.text:
            return response.text.strip()
        elif response.parts:
             return "".join(part.text for part in response.parts).strip()
        else:
            log_message("Gemini API response did not contain text or parts.")
            if hasattr(response, 'candidates') and response.candidates and response.candidates[0].finish_reason != 'STOP':
                log_message(f"Gemini generation stopped due to: {response.candidates[0].finish_reason}")
                if response.candidates[0].safety_ratings:
                    log_message(f"Safety Ratings: {response.candidates[0].safety_ratings}")
            return "My pun generator just blue-screened. Try again later!"
    except Exception as e:
        log_message(f"Error calling Gemini API: {e}")
        return "My AI brain just short-circuited. I'll be back!"

# --- Main Bot Logic ---
def run_bot():
    if not gemini_model:
        log_message("Exiting bot: Gemini model not initialized or API key issue.")
        return
    if not sid:
        log_message("Exiting bot: Sentiment analyzer (VADER) not loaded.")
        return

    log_message("Initializing Reddit instance...")
    if REDDIT_BOT_PASSWORD == "4805640@Kmt" or REDDIT_BOT_USERNAME == "All_Gas_No_Brakes": # Simplified check
        log_message("CRITICAL ERROR: Update placeholder REDDIT_BOT_USERNAME and REDDIT_BOT_PASSWORD with your bot's actual credentials.")
        return

    try:
        reddit = praw.Reddit(
            client_id=REDDIT_CLIENT_ID,
            client_secret=REDDIT_CLIENT_SECRET,
            user_agent=REDDIT_USER_AGENT,
            username=REDDIT_BOT_USERNAME,
            password=REDDIT_BOT_PASSWORD,
        )
        me = reddit.user.me()
        if me is None:
            log_message(f"Failed to log in to Reddit as {REDDIT_BOT_USERNAME}. reddit.user.me() returned None. Check credentials and account status.")
            return
        log_message(f"Successfully logged in as Reddit user: {me}")
    except Exception as e:
        log_message(f"Failed to log in to Reddit: {e}")
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

            for post in subreddit.hot(limit=15): # Scan a few more posts
                if post.id in processed_items or post.stickied:
                    continue
                if post.author and post.author.name.lower() == REDDIT_BOT_USERNAME.lower():
                    continue
                if post.archived or post.locked:
                    continue

                post_content_for_sentiment = post.title + " " + post.selftext
                sentiment = get_sentiment_score(post_content_for_sentiment)
                log_message(f"Post '{post.title[:30].replace(os.linesep, ' ')}...' (ID: {post.id}) sentiment: {sentiment:.2f}")

                if sentiment < -0.2:
                    log_message(f"Skipping post {post.id} due to negative sentiment ({sentiment:.2f}).")
                    save_processed_item(post.id)
                    continue
                
                post.comments.replace_more(limit=0) 
                comments_to_consider = [
                    c for c in post.comments.list()[:20] # Look at more comments
                    if c.author and c.author.name.lower() != REDDIT_BOT_USERNAME.lower() and c.id not in processed_items and not c.stickied
                ]

                if not comments_to_consider:
                    # log_message(f"No suitable new comments found for post {post.id}. Skipping post for comment replies this time.")
                    # save_processed_item(post.id) # Don't mark post as fully processed yet, just for this pass
                    continue # Try next post
                
                target_comment = random.choice(comments_to_consider)

                log_message(f"Selected comment (ID: {target_comment.id}) by u/{target_comment.author.name if target_comment.author else '[deleted]'} under post '{post.title[:30].replace(os.linesep, ' ')}...'")
                # log_message(f"  Comment Body: {target_comment.body[:80].replace(os.linesep, ' ')}...")

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
                        time.sleep(10) 
                        break # Break from posts loop after one reply in cycle
                    except praw.exceptions.APIException as e:
                        log_message(f"Reddit API Exception while replying to comment {target_comment.id}: {e}")
                        if "RATELIMIT" in str(e).upper():
                            log_message("Rate limit hit. Sleeping for 5 minutes.")
                            time.sleep(300)
                        elif any(err_str in str(e).upper() for err_str in ["DELETED_COMMENT", "TOO_OLD", "THREAD_LOCKED", "COMMENT_DELETED", "NOT_AUTHOR", "PARENT_DELETED"]):
                            log_message(f"Comment/Post issue for {target_comment.id}. Marking comment as processed.")
                            save_processed_item(target_comment.id)
                        else: # Other API errors
                            log_message(f"Unhandled API exception for {target_comment.id}. Marking as processed to avoid loop.")
                            save_processed_item(target_comment.id)
                    except Exception as e:
                        log_message(f"An unexpected error occurred while replying to comment {target_comment.id}: {e}")
                        save_processed_item(target_comment.id) 
                else:
                    log_message(f"Gemini did not generate a suitable reply for comment {target_comment.id}.")
                    save_processed_item(target_comment.id)
                
                time.sleep(random.uniform(2,5)) # Small random delay

            if not replied_in_cycle:
                log_message("No new suitable posts/comments found to reply to in this cycle across scanned posts.")

            log_message(f"--- Cycle finished. Waiting for {REPLY_INTERVAL_SECONDS // 60} minutes before next scan. ---")
            time.sleep(REPLY_INTERVAL_SECONDS)

        except praw.exceptions.PRAWException as e: # More general PRAW errors
            log_message(f"A PRAW specific error occurred: {e}")
            log_message("Sleeping for 60 seconds before retrying...")
            time.sleep(60)
        except KeyboardInterrupt:
            log_message("KeyboardInterrupt received. Shutting down bot...")
            break # Exit the while True loop
        except Exception as e:
            log_message(f"An critical unexpected error occurred in the main loop: {e}")
            log_message(f"Error type: {type(e).__name__}")
            log_message("Sleeping for 5 minutes before retrying the loop...")
            time.sleep(300)


if __name__ == "__main__":
    log_message("Starting Reddit Bot All_Gas_No_Brakes...")

    if REDDIT_BOT_USERNAME == "All_Gas_No_Brakes" or REDDIT_BOT_PASSWORD == "4805640@Kmt": # Check again
        log_message("CRITICAL ERROR: Bot username or password are still placeholders. Please edit the script.")
    elif not GEMINI_API_KEY or "YOUR_GEMINI_API_KEY" in GEMINI_API_KEY or "AIzaSyC" not in GEMINI_API_KEY :
        log_message("CRITICAL ERROR: Gemini API key is missing or a placeholder. Please edit the script.")
    elif sid is None:
        log_message("CRITICAL ERROR: Sentiment analyzer (VADER) failed to load. Please ensure NLTK data is downloaded (vader_lexicon, punkt).")
    elif gemini_model is None:
        log_message("CRITICAL ERROR: Gemini model failed to initialize. Check API key and internet connection.")
    else:
        run_bot()
    log_message("Bot script finished or exited.")