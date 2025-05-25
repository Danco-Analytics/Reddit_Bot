import time
import random
import praw
import google.generativeai as genai

# === CONFIGURATION ===

REDDIT_USERNAME = "All_Gas_No_Brakes"
REDDIT_PASSWORD = "4805640@Kmt"
REDDIT_CLIENT_ID = "vEW0UrVrMw9rAc8VAtr_lg"
REDDIT_CLIENT_SECRET = "tyhSZUJ9fnFLhHh_SkPRfHKzmSom_g"
USER_AGENT = "All_Gas_No_BrakesBot/1.0 by u/All_Gas_No_Brakes"

GEMINI_API_KEY = "AIzaSyCOyiZkk8t7zFtX4zC9G4v66MPJfgjIi84"

SUBREDDITS = [
    "technology", "worldnews", "AskReddit",
    "Kenya", "MachineLearning", "conspiracy", "offmychest",
    "todayilearned", "unpopularopinion"
]

# === INITIALIZE GEMINI ===

genai.configure(api_key=GEMINI_API_KEY)
gemini = genai.GenerativeModel("gemini-pro")

# === INITIALIZE REDDIT ===

reddit = praw.Reddit(
    client_id=REDDIT_CLIENT_ID,
    client_secret=REDDIT_CLIENT_SECRET,
    username=REDDIT_USERNAME,
    password=REDDIT_PASSWORD,
    user_agent=USER_AGENT
)

# === TRACK REPLIED POSTS ===
replied_post_ids = set()

# === GENERATE A HUMAN-LIKE WITTY REPLY ===

def generate_reply(title, body):
    prompt = f"""
You're a witty, sarcastic, and sometimes deeply insightful Reddit user who replies with casual humor, pop culture references, light cussing (nothing offensive), and real empathy. Sometimes you roast, sometimes you're thoughtful — depends on the tone of the post.

NEVER sound like a bot. Avoid formal language, buzzwords, or AI-sounding garbage. Make your reply original, fresh, and personal, like you’re truly reacting to the post. It’s okay to use slang, memes, Gen Z phrases, or emojis — just don’t be cringe.

Here’s the Reddit post you’re replying to:

TITLE: {title}
BODY: {body if body else "[No body text provided]"}

Write your Reddit comment in 2–4 sentences. Keep it real. Give 'em something to think about or laugh at.
    """
    try:
        response = gemini.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"[Gemini Error] {e}")
        return None

# === PROCESS SUBREDDIT POSTS ===

def process_subreddit(sub_name):
    print(f"\n[🔥] Diving into r/{sub_name}...")
    subreddit = reddit.subreddit(sub_name)
    for post in subreddit.new(limit=6):
        if post.id in replied_post_ids or post.author == REDDIT_USERNAME:
            continue

        try:
            reply = generate_reply(post.title, post.selftext)
            if reply:
                post.reply(reply)
                print(f"[💬] Replied to: \"{post.title}\"")
                replied_post_ids.add(post.id)
                time.sleep(random.randint(8, 18))  # chill delay
        except Exception as err:
            print(f"[⚠️] Couldn't reply to post {post.id}: {err}")

# === MAIN LOOP ===

def main():
    while True:
        sub = random.choice(SUBREDDITS)
        process_subreddit(sub)
        print("[😴] Nap time... back in 15 minutes.\n")
        time.sleep(900)

if __name__ == "__main__":
    main()
