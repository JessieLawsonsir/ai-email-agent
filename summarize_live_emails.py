from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from transformers import T5Tokenizer, T5ForConditionalGeneration
import torch
import base64
import os
import email

# 🔐 Gmail read-only access scope
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# 🎯 Load FLAN-T5 Model for summarization
tokenizer = T5Tokenizer.from_pretrained("google/flan-t5-small")
model = T5ForConditionalGeneration.from_pretrained("google/flan-t5-small")

def authenticate_gmail():
    creds = None
    # Use stored token if available
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    else:
        # Authenticate and store token
        flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
        creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    return build("gmail", "v1", credentials=creds)

def summarize(text):
    prompt = f"Summarize this customer support request briefly and clearly: {text}"
    inputs = tokenizer(prompt, return_tensors="pt", max_length=512, truncation=True)
    summary_ids = model.generate(inputs["input_ids"], max_length=100, num_beams=4, early_stopping=True)
    return tokenizer.decode(summary_ids[0], skip_special_tokens=True)

def get_unread_emails(service):
    print("📥 Fetching unread emails...")
    results = service.users().messages().list(userId="me", labelIds=["INBOX"], q="is:unread").execute()
    messages = results.get("messages", [])

    if not messages:
        print("✅ No unread messages.")
        return

    print(f"🔔 Found {len(messages)} unread message(s):\n")

    for msg in messages:
        msg_data = service.users().messages().get(userId="me", id=msg["id"], format="full").execute()
        payload = msg_data["payload"]
        headers = payload.get("headers", [])
        subject = [h["value"] for h in headers if h["name"] == "Subject"]
        subject = subject[0] if subject else "(No Subject)"

        # Extract plain text body
        parts = payload.get("parts", [])
        body = ""
        for part in parts:
            if part.get("mimeType") == "text/plain":
                data = part.get("body", {}).get("data")
                if data:
                    decoded = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
                    body = decoded.strip()
                    break

        if body:
            print(f"📧 Subject: {subject}")
            print(f"📝 Original Body:\n{body}")
            summary = summarize(body)
            print(f"📌 Summary: {summary}")
            print("-" * 60)
        else:
            print(f"📧 Subject: {subject}")
            print("⚠️ No plain-text body found.")
            print("-" * 60)

if __name__ == "__main__":
    service = authenticate_gmail()
    get_unread_emails(service)
