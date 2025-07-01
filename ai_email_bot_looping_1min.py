import os
import json
import time
import pickle
import datetime
from email.mime.text import MIMEText
from base64 import urlsafe_b64encode

import firebase_admin
from firebase_admin import credentials, db

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from marketing_agent_safe import ask_chatgpt

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
FIREBASE_CRED_FILE = "firebase-creds.json"
FIREBASE_DB_URL = "https://prebid-email-bot.firebaseio.com/"
TOKEN_FILE = "token.pickle"
RESPONSES_DIR = "responses"

def get_gmail_service():
    with open(TOKEN_FILE, 'rb') as token:
        creds = pickle.load(token)
    return build('gmail', 'v1', credentials=creds)

def load_responses():
    with open(os.path.join(RESPONSES_DIR, "membership_responses.json"), "r") as f:
        membership = json.load(f)
    with open(os.path.join(RESPONSES_DIR, "marketing_responses.json"), "r") as f:
        marketing = json.load(f)
    return membership, marketing

def classify_question_gpt(question):
    from openai import OpenAI
    client = OpenAI()
    system_prompt = (
        "You are a classification assistant for Prebid.org. "
        "Given the user message below, classify it as either 'membership', 'marketing', or 'other'. "
        "Also guess which instruction set (marketing or membership) is more useful if 'other'. "
        "Respond in this JSON format: {\"category\": \"...\", \"best_instruction_set\": \"...\"}"
    )
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question}
        ]
    )
    try:
        parsed = json.loads(response.choices[0].message.content)
        return parsed["category"], parsed["best_instruction_set"]
    except:
        return "other", "marketing"

def match_response(question, response_bank):
    from openai import OpenAI
    client = OpenAI()
    prompt = (
        "You are a semantic matching engine. Given the following saved questions:\n" +
        "\n".join(f"- {q}" for q in response_bank.keys()) +
        f"\n\nFind the closest question that matches this:\n\"{question}\"\n"
        "If none are appropriate, respond ONLY with: NONE"
    )
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )
    result = response.choices[0].message.content.strip()
    return result if result in response_bank else None

def send_reply(service, message_id, to_email, subject, body_text):
    message = MIMEText(body_text)
    message["to"] = to_email
    message["subject"] = f"Re: {subject}"
    raw = urlsafe_b64encode(message.as_bytes()).decode()
    service.users().messages().send(userId="me", body={"raw": raw}).execute()
    service.users().messages().modify(userId="me", id=message_id, body={"removeLabelIds": ["UNREAD"]}).execute()

def log_to_firebase(entry):
    ref = db.reference("/emails")
    ref.push(entry)

def process_emails():
    membership, marketing = load_responses()
    gmail = get_gmail_service()

    results = gmail.users().messages().list(userId="me", labelIds=["INBOX"], q="is:unread").execute()
    messages = results.get("messages", [])

    for m in messages:
        msg = gmail.users().messages().get(userId="me", id=m["id"], format="full").execute()
        headers = msg["payload"]["headers"]
        sender = next(h["value"] for h in headers if h["name"] == "From")
        subject = next((h["value"] for h in headers if h["name"] == "Subject"), "(no subject)")
        snippet = msg.get("snippet", "")

        category, instruction_set = classify_question_gpt(snippet)
        responses = membership if instruction_set == "membership" else marketing
        match = match_response(snippet, responses)

        if match:
            reply = responses[match]
        else:
            reply = ask_chatgpt(snippet, websites=[], use_history=True)

        send_reply(gmail, m["id"], sender, subject, reply)

        log_to_firebase({
            "sender": sender,
            "subject": subject,
            "message": snippet,
            "category": category,
            "matched_question": match or "None",
            "response": reply,
            "timestamp": datetime.datetime.now().isoformat()
        })

def main():
    cred = credentials.Certificate(FIREBASE_CRED_FILE)
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred, {'databaseURL': FIREBASE_DB_URL})

    print("📬 Email bot started. Checking inbox every 1 minute...")
    while True:
        try:
            process_emails()
        except Exception as e:
            print("❌ Error:", e)
        time.sleep(60)

if __name__ == "__main__":
    main()
