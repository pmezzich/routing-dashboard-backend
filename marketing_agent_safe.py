import argparse
import os
from dotenv import load_dotenv
from openai import OpenAI
from scraper import scrape_website_text
from datetime import date
import tiktoken

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

HISTORY_FILE = "session_history.txt"
MAX_PROMPT_TOKENS = 4000
MAX_RESPONSE_TOKENS = 1000

def load_websites():
    try:
        with open("websites.txt", "r") as file:
            return [line.strip() for line in file if line.strip()]
    except FileNotFoundError:
        print("⚠️ websites.txt not found. No website content will be included.")
        return []

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    return ""

def save_to_history(user_msg, ai_msg):
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write("User: " + user_msg + "\n")
        f.write("AI: " + ai_msg + "\n\n")

def reset_history():
    open(HISTORY_FILE, "w").close()

def num_tokens_from_string(string, model="gpt-4o"):
    encoding = tiktoken.encoding_for_model(model)
    return len(encoding.encode(string))

def truncate_to_token_limit(text, model="gpt-4o", max_tokens=2000):
    encoding = tiktoken.encoding_for_model(model)
    tokens = encoding.encode(text)
    truncated = encoding.decode(tokens[:max_tokens])
    return truncated

def ask_chatgpt(question, websites, use_history=True):
    website_contexts = []
    for url in websites:
        content = scrape_website_text(url)
        truncated_content = truncate_to_token_limit(content, max_tokens=1000)
        website_contexts.append(f"From {url}:\n{truncated_content}\n")

    prompt_intro = "\n\n".join(website_contexts)
    today = date.today().strftime("%B %d, %Y")

    conversation_history = load_history() if use_history else ""
    user_input = "User: " + question
    full_prompt = conversation_history + "\n" + user_input

    total_prompt = prompt_intro + "\n\n" + full_prompt
    token_count = num_tokens_from_string(total_prompt)

    if token_count > MAX_PROMPT_TOKENS:
        full_prompt = truncate_to_token_limit(full_prompt, max_tokens=MAX_PROMPT_TOKENS - num_tokens_from_string(prompt_intro))
        total_prompt = prompt_intro + "\n\n" + full_prompt

    response = client.chat.completions.create(
        model="gpt-4o",
        max_tokens=MAX_RESPONSE_TOKENS,
        messages=[
            {
                "role": "system",
                "content": (
                    f"You are a helpful marketing assistant for Prebid. Today's date is {today}. "
                    "Use the provided website content and previous conversation history to answer the user's question. "
                    "When asked about upcoming events, only include events occurring today or later. "
                    "When asked about past events, only include events before today. "
                    "If the information is in websites.txt always use that information. "
                    "At the end of every response, remind the user to follow Prebid on LinkedIn and subscribe to the newsletter for updates."
                    "Here is the info on membership options if asked: Prebid Membership Tiers & Pricing. Buyer (Brands & Agencies): $6,000/year (for companies with over $10M in revenue). Publisher: $6,000/year (for companies with over $10M in revenue). Technology (Ad-tech and Mar-tech Partners): $7,500/year for companies with under $5M revenue, $15,000/year for companies with $5–10M revenue, $30,000/year for companies with over $10M revenue. Leadership: $50,000/year (for companies with over $10M in revenue). Fellowship: Free (one-year application-based membership for mission-aligned organizations). Tier Comparison – Benefits. Leadership: No board seat, PMC participation, Private Slack access, Can participate in Prebid.org events, Logo displayed on Prebid.org website. Technology: Elect a board representative, PMC participation, Private Slack access, Can participate in Prebid.org events, Logo displayed on Prebid.org website. Publisher: Elect a board representative, PMC participation, Private Slack access, Can participate in Prebid.org events, Logo displayed on Prebid.org website. Buyer: Elect a board representative, PMC participation, Private Slack access, Can participate in Prebid.org events, Logo displayed on Prebid.org website. Fellowship (one-year tenure): No board seat, PMC participation, Private Slack access, Can participate in Prebid.org events, No logo on Prebid.org website."
                )
            },
            {
                "role": "user",
                "content": total_prompt
            },
        ],
        temperature=0.5,
    )

    answer = response.choices[0].message.content.strip()
    save_to_history(question, answer)
    return answer
