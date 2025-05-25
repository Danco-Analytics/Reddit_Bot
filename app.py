import praw
import google.generativeai as genai
import time
import os
import random

REDDIT_CLIENT_ID = "vEW0UrVrMw9rAc8VAtr_lg"
REDDIT_CLIENT_SECRET = "tyhSZUJ9fnFLhHh_SkPRfHKzmSom_g"
REDDIT_USER_AGENT = "All_Gas_No_Brakes_Bot v0.1 by u/No_Court_5398"
REDDIT_BOT_USERNAME = "YOUR_BOT_USERNAME_HERE"
REDDIT_BOT_PASSWORD = "YOUR_BOT_PASSWORD_HERE"

GEMINI_API_KEY = "AIzaSyCOyiZkk8t7zFtX4zC9G4v66MPJfgjIi84"

TARGET_SUBREDDITS = ["learnpython", "AskReddit", "testingground4bots", "BotTown"]
REPLY_INTERVAL_SECONDS = 15 * 60
PROCESSED_POSTS_FILE = "processed_posts_gemini.txt"
BOT_DISCLAIMER = "\n\n---\n\n*I am an AI bot powered by Gemini. This reply is automated. Please use your discretion.*"

gemini_model = None
try:
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel('gemini-pro')
    print("Gemini API configured successfully.")
except Exception as e:
    print(f"Error configuring Gemini API: {e}")

def load_processed_posts():
    if not os.path.exists(PROCESSED_POSTS_FILE):
        return set()
    try:
        with open(PROCESSED_POSTS_FILE, "r") as f:
            return set(line.strip() for line in f)
    except Exception as e:
        print(f"Error loading processed posts file: {e}")
        return set()

def save_processed_post(post_id):
    try:
        with open(PROCESSED_POSTS_FILE, "a") as f:
            f.write(post_id + "\n")
    except Exception as e:
        print(f"Error saving processed post ID {post_id}: {e}")

def generate_gemini_reply(post_title, post_body):
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
        if hasattr(response, 'text') and response.text:
            return response.text.strip()
        elif response.parts:
             return "".join(part.text for part in response.parts).strip()
        else:
            print("Gemini API response did not contain text or parts.")
            if response.candidates and response.candidates[0].finish_reason != 'STOP':
                print(f"Gemini generation stopped due to: {response.candidates[0].finish_reason}")
                if response.candidates[0].safety_ratings:
                    print(f"Safety Ratings: {response.candidates[0].safety_ratings}")
            return "I had a thought, but it seems I lost it! Sorry about that."
    except Exception as e:
        print(f"Error calling Gemini API: {e}")
        return "Sorry, I encountered an error trying to think of a reply."

def run_bot():
    if not gemini_model:
        print("Exiting bot as Gemini model is not available.")
        return

    print("Initializing Reddit instance...")
    if REDDIT_BOT_USERNAME == "YOUR_BOT_USERNAME_HERE" or REDDIT_BOT_PASSWORD == "YOUR_BOT_PASSWORD_HERE":
        print("CRITICAL ERROR: You MUST set your bot's Reddit username and password (REDDIT_BOT_USERNAME, REDDIT_BOT_PASSWORD).")
        return

    try:
        reddit = praw.Reddit(
            client_id=REDDIT_CLIENT_ID,
            client_secret=REDDIT_CLIENT_SECRET,
            user_agent=REDDIT_USER_AGENT,
            username=REDDIT_BOT_USERNAME,
            password=REDDIT_BOT_PASSWORD,
        )
        print(f"Successfully logged in as Reddit user: {reddit.user.me()}")
    except Exception as e:
        print(f"Failed to log in to Reddit: {e}")
        return

    processed_posts = load_processed_posts()
    print(f"Loaded {len(processed_posts)} processed post IDs.")

    while True:
        try:
            print(f"\n--- Starting new scan cycle at {time.ctime()} ---")
            subreddit_to_scan = random.choice(TARGET_SUBREDDITS)
            print(f"Scanning subreddit: r/{subreddit_to_scan}")
            subreddit = reddit.subreddit(subreddit_to_scan)

            posts_found_in_cycle = 0
            replied_in_cycle = False

            for post in subreddit.hot(limit=10):
                posts_found_in_cycle +=1
                if post.id in processed_posts:
                    continue
                if post.author and post.author.name.lower() == REDDIT_BOT_USERNAME.lower():
                    continue
                if post.archived or post.locked:
                    continue
                
                print(f"\nFound new post in r/{subreddit_to_scan}:")
                print(f"  ID: {post.id}")
                print(f"  Title: {post.title}")
                print(f"  Author: u/{post.author.name if post.author else '[deleted]'}")

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
                        time.sleep(5) 
                        break 
                    except praw.exceptions.APIException as e:
                        print(f"Reddit API Exception while replying: {e}")
                        if "RATELIMIT" in str(e).upper():
                            print("Rate limit hit. Sleeping for 60 seconds before trying next cycle.")
                            time.sleep(60)
                        elif "DELETED_COMMENT" in str(e).upper() or "TOO_OLD" in str(e).upper():
                            print("Post was deleted or too old to comment. Marking as processed.")
                            save_processed_post(post.id)
                            processed_posts.add(post.id)  
                    except Exception as e:
                        print(f"An unexpected error occurred while replying: {e}")
                else:
                    print(f"Gemini did not generate a suitable reply for post {post.id}.")
                
                time.sleep(2)

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
    if GEMINI_API_KEY == "AIzaSyCOyiZkk8t7zFtX4zC9G4v66MPJfgjIi84" or "YOUR_GEMINI_API_KEY" in GEMINI_API_KEY : # Basic check
        print("INFO: Using the provided Gemini API key. Ensure it is correct and active.")
    
    if REDDIT_BOT_USERNAME == "YOUR_BOT_USERNAME_HERE" or REDDIT_BOT_PASSWORD == "YOUR_BOT_PASSWORD_HERE":
        print("CRITICAL ERROR: You MUST set your bot's Reddit username and password (REDDIT_BOT_USERNAME, REDDIT_BOT_PASSWORD) in the script.")
        print("This should be for a dedicated bot account, NOT your personal Reddit account or developer account.")
    else:
        run_bot()