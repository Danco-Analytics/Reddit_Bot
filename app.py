import praw
import google.generativeai as genai
import time
import os
import random

# --- Configuration ---
# !! IMPORTANT: Replace with your actual credentials, preferably from environment variables !!
# Example for environment variables:
# REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
# REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
# REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT")
# REDDIT_USERNAME = os.getenv("REDDIT_USERNAME") # Your BOT's username
# REDDIT_PASSWORD = os.getenv("REDDIT_PASSWORD") # Your BOT's password
# GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# --- Replace these with your actual credentials or load from environment variables ---
# --- For security, it's STRONGLY recommended to use environment variables ---
REDDIT_CLIENT_ID = "vEW0UrVrMw9rAc8VAtr_lg"  # Your personal use script ID
REDDIT_CLIENT_SECRET = "tyhSZUJ9fnFLhHh_SkPRfHKzmSom_g" # Your secret
REDDIT_USER_AGENT = "All_Gas_No_Brakes_Bot v0.1 by u/No_Court_5398" # App name and your main username
REDDIT_BOT_USERNAME = "YOUR_BOT_USERNAME_HERE"  # The username of the DEDICATED BOT ACCOUNT
REDDIT_BOT_PASSWORD = "YOUR_BOT_PASSWORD_HERE"  # The password of the DEDICATED BOT ACCOUNT

GEMINI_API_KEY = "AIzaSyCOyiZkk8t7zFtX4zC9G4v66MPJfgjIi84" # YOUR GEMINI API KEY - KEEP THIS SECRET

# --- Bot Settings ---
TARGET_SUBREDDITS = ["learnpython", "AskReddit", "testingground4bots", "BotTown"] # Customize this list
REPLY_INTERVAL_SECONDS = 15 * 60  # 15 minutes
PROCESSED_POSTS_FILE = "processed_posts_gemini.txt" # File to store IDs of replied-to posts
BOT_DISCLAIMER = "\n\n---\n\n*I am an AI bot powered by Gemini. This reply is automated. Please use your discretion.*"

# --- Initialize Gemini ---
try:
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel('gemini-pro') # Or other suitable model
    print("Gemini API configured successfully.")
except Exception as e:
    print(f"Error configuring Gemini API: {e}")
    gemini_model = None # Ensure model is None if setup fails

# --- Helper Functions ---
def load_processed_posts():
    """Loads IDs of posts already replied to."""
    if not os.path.exists(PROCESSED_POSTS_FILE):
        return set()
    try:
        with open(PROCESSED_POSTS_FILE, "r") as f:
            return set(line.strip() for line in f)
    except Exception as e:
        print(f"Error loading processed posts file: {e}")
        return set()

def save_processed_post(post_id):
    """Saves a post ID as processed."""
    try:
        with open(PROCESSED_POSTS_FILE, "a") as f:
            f.write(post_id + "\n")
    except Exception as e:
        print(f"Error saving processed post ID {post_id}: {e}")

def generate_gemini_reply(post_title, post_body):
    """
    Generates a reply using the Gemini API based on post content.
    """
    if not gemini_model:
        print("Gemini model not initialized. Cannot generate reply.")
        return "Sorry, I am currently unable to generate a response."

    prompt = f"""You are a Reddit bot. Your goal is to provide a helpful, relevant, and concise comment on the following Reddit post.
    Try to sound like a regular Reddit user, but keep it civil and on-topic.
    Do not explicitly state you are an AI in the main body of your reply, the disclaimer will be added later.

    Post Title: "{post_title}"
    Post Body (if any): "{post_body if post_body else 'No body content.'}"

    Generate a relevant comment for this post:
    """
    try:
        print(f"\nGenerating Gemini reply for post: \"{post_title[:50]}...\"")
        response = gemini_model.generate_content(prompt)
        # Check if response has 'text' attribute. Sometimes it might be in parts.
        if hasattr(response, 'text') and response.text:
            return response.text.strip()
        elif response.parts: # Handle multi-part responses if any
             return "".join(part.text for part in response.parts).strip()
        else:
            print("Gemini API response did not contain text or parts.")
            # Log the full response for debugging if needed
            # print(f"Full Gemini response: {response}")
            # Check candidate and safety ratings if available
            if response.candidates and response.candidates[0].finish_reason != 'STOP':
                print(f"Gemini generation stopped due to: {response.candidates[0].finish_reason}")
                if response.candidates[0].safety_ratings:
                    print(f"Safety Ratings: {response.candidates[0].safety_ratings}")
            return "I had a thought, but it seems I lost it! Sorry about that."

    except Exception as e:
        print(f"Error calling Gemini API: {e}")
        # Log the full error or response for debugging if needed
        return "Sorry, I encountered an error trying to think of a reply."


# --- Main Bot Logic ---
def run_bot():
    if not gemini_model:
        print("Exiting bot as Gemini model is not available.")
        return

    print("Initializing Reddit instance...")
    if not all([REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT, REDDIT_BOT_USERNAME, REDDIT_BOT_PASSWORD]):
        print("Reddit credentials are not fully set. Please check your configuration.")
        print(f"ID: {'Set' if REDDIT_CLIENT_ID else 'Not Set'}")
        print(f"Secret: {'Set' if REDDIT_CLIENT_SECRET else 'Not Set'}")
        print(f"Agent: {'Set' if REDDIT_USER_AGENT else 'Not Set'}")
        print(f"Username: {'Set' if REDDIT_BOT_USERNAME else 'Not Set'}")
        print(f"Password: {'Set' if REDDIT_BOT_PASSWORD else 'Not Set'}")

        # Check if using placeholder credentials, which will likely fail authentication.
        if REDDIT_BOT_USERNAME == "YOUR_BOT_USERNAME_HERE" or REDDIT_BOT_PASSWORD == "YOUR_BOT_PASSWORD_HERE":
            print("ERROR: You are using placeholder Reddit username/password. Please update them.")
            return
        # It's okay if Client ID/Secret are placeholders if the user is aware, but username/password must be real.

    try:
        reddit = praw.Reddit(
            client_id=REDDIT_CLIENT_ID,
            client_secret=REDDIT_CLIENT_SECRET,
            user_agent=REDDIT_USER_AGENT,
            username=REDDIT_BOT_USERNAME,
            password=REDDIT_BOT_PASSWORD,
            #praw.ini can also be used for configuration
        )
        print(f"Successfully logged in as Reddit user: {reddit.user.me()}")
    except Exception as e:
        print(f"Failed to log in to Reddit: {e}")
        print("Please ensure your Reddit credentials (client_id, client_secret, bot username, bot password) are correct and the bot account has API access enabled if necessary.")
        return

    processed_posts = load_processed_posts()
    print(f"Loaded {len(processed_posts)} processed post IDs.")

    while True:
        try:
            print(f"\n--- Starting new scan cycle at {time.ctime()} ---")
            subreddit_to_scan = random.choice(TARGET_SUBREDDITS)
            print(f"Scanning subreddit: r/{subreddit_to_scan}")
            subreddit = reddit.subreddit(subreddit_to_scan)

            # Fetch a few hot posts. You can also use .new() or .top()
            # Limit to avoid too many API calls if subreddit is very active
            posts_found_in_cycle = 0
            replied_in_cycle = False

            for post in subreddit.hot(limit=10): # Look at top 10 hot posts
                posts_found_in_cycle +=1
                if post.id in processed_posts:
                    # print(f"Skipping already processed post: {post.id} - \"{post.title[:30]}...\"")
                    continue

                if post.author and post.author.name.lower() == REDDIT_BOT_USERNAME.lower():
                    # print(f"Skipping own post: {post.id}")
                    continue

                if post.archived or post.locked:
                    # print(f"Skipping archived/locked post: {post.id}")
                    continue
                
                print(f"\nFound new post in r/{subreddit_to_scan}:")
                print(f"  ID: {post.id}")
                print(f"  Title: {post.title}")
                print(f"  Author: u/{post.author.name if post.author else '[deleted]'}")

                # Generate reply using Gemini
                # Use post.title and post.selftext (body of text posts)
                reply_text_base = generate_gemini_reply(post.title, post.selftext)
                
                if reply_text_base and "unable to generate" not in reply_text_base and "lost it" not in reply_text_base :
                    full_reply_text = reply_text_base + BOT_DISCLAIMER
                    
                    print(f"Attempting to reply: \"{full_reply_text[:100].replace(BOT_DISCLAIMER, '')}...\"")
                    try:
                        post.reply(full_reply_text)
                        print(f"Successfully replied to post ID {post.id} in r/{subreddit_to_scan}")
                        save_processed_post(post.id)
                        processed_posts.add(post.id)
                        replied_in_cycle = True
                        # Short pause after a successful reply before breaking and waiting for the main interval
                        time.sleep(5) 
                        break # Break from the inner loop (posts loop) after one reply
                    except praw.exceptions.APIException as e:
                        print(f"Reddit API Exception while replying: {e}")
                        if "RATELIMIT" in str(e).upper():
                            print("Rate limit hit. Sleeping for 60 seconds before trying next cycle.")
                            time.sleep(60) # Sleep longer if rate limited
                            # No 'break' here, will go to main sleep eventually
                        elif "DELETED_COMMENT" in str(e).upper() or "TOO_OLD" in str(e).upper():
                            print("Post was deleted or too old to comment. Marking as processed.")
                            save_processed_post(post.id)
                            processed_posts.add(post.id)
                        # Add more specific error handling if needed    
                    except Exception as e:
                        print(f"An unexpected error occurred while replying: {e}")
                else:
                    print(f"Gemini did not generate a suitable reply for post {post.id}.")
                
                time.sleep(2) # Small delay between checking posts to be nice to Reddit API

            if not posts_found_in_cycle:
                print(f"No posts found in r/{subreddit_to_scan} in this iteration (or all were unsuitable).")
            elif not replied_in_cycle:
                print(f"Scanned {posts_found_in_cycle} posts in r/{subreddit_to_scan}, but made no new replies in this cycle.")

            print(f"--- Cycle finished. Waiting for {REPLY_INTERVAL_SECONDS // 60} minutes before next scan. ---")
            time.sleep(REPLY_INTERVAL_SECONDS)

        except praw.exceptions.PRAWException as e:
            print(f"A PRAW specific error occurred: {e}")
            print("Sleeping for 60 seconds before retrying...")
            time.sleep(60)
        except Exception as e:
            print(f"An unexpected error occurred in the main loop: {e}")
            print("Sleeping for 60 seconds before retrying...")
            time.sleep(60)

if __name__ == "__main__":
    if GEMINI_API_KEY == "AIzaSyCOyiZkk8t7zFtX4zC9G4v66MPJfgjIi84" or GEMINI_API_KEY == "YOUR_GEMINI_API_KEY_HERE":
        print("WARNING: You are using a placeholder or the example Gemini API key.")
        print("Please replace it with your actual Gemini API key in the script or via environment variables.")
        # You might want to exit here if the key is clearly a placeholder and not intended for use
        # exit() 
    
    if REDDIT_BOT_USERNAME == "YOUR_BOT_USERNAME_HERE" or REDDIT_BOT_PASSWORD == "YOUR_BOT_PASSWORD_HERE":
        print("CRITICAL ERROR: You MUST set your bot's Reddit username and password (REDDIT_BOT_USERNAME, REDDIT_BOT_PASSWORD).")
        print("These are different from your Reddit App's developer (No_Court_5398) or App Name (All_Gas_No_Brakes).")
        print("Please create a dedicated Reddit account for your bot and use its credentials.")
    elif REDDIT_CLIENT_ID == "YOUR_CLIENT_ID" or REDDIT_CLIENT_SECRET == "YOUR_CLIENT_SECRET":
         print("WARNING: You are using placeholder Reddit Client ID/Secret. Ensure these are correctly set.")
    else:
        run_bot()
