from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from transformers import T5Tokenizer, T5ForConditionalGeneration
import mysql.connector
import base64
import os
import email
from dotenv import load_dotenv

# ✅ Load environment variables
load_dotenv()

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# ✅ Load tokenizer and model
tokenizer = T5Tokenizer.from_pretrained("google/flan-t5-base")
model = T5ForConditionalGeneration.from_pretrained("google/flan-t5-base")

# ✅ Gmail authentication
def authenticate_gmail():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    else:
        flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
        creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    return build("gmail", "v1", credentials=creds)

# ✅ Summarize email body
def summarize(text):
    clean_text = text.strip().replace('\n', ' ').replace('\r', ' ')
    prompt = f"Summarize this customer email clearly and briefly: {clean_text}"
    inputs = tokenizer(prompt, return_tensors="pt", max_length=512, truncation=True)
    summary_ids = model.generate(inputs["input_ids"], max_length=80)
    return tokenizer.decode(summary_ids[0], skip_special_tokens=True)

# ✅ Store data into MySQL
def store_summary(message_id, sender, subject, body, summary):
    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME")
        )
        cursor = conn.cursor()
        cursor.execute("""
            INSERT IGNORE INTO email_summaries (message_id, sender, subject, body, summary)
            VALUES (%s, %s, %s, %s, %s)
        """, (message_id, sender, subject, body, summary))
        conn.commit()
        cursor.close()
        conn.close()
        print("✅ Stored in DB\n")
    except mysql.connector.Error as err:
        print(f"❌ DB Error: {err}")

# ✅ Read and process unread emails
def process_emails(service):
    print("📥 Fetching unread emails...")
    results = service.users().messages().list(userId="me", labelIds=["INBOX"], q="is:unread").execute()
    messages = results.get("messages", [])

    if not messages:
        print("✅ No unread emails.")
        return

    for msg in messages:
        msg_data = service.users().messages().get(userId="me", id=msg["id"], format="full").execute()
        payload = msg_data.get("payload", {})
        headers = payload.get("headers", [])

        # Extract info
        subject = next((h["value"] for h in headers if h["name"] == "Subject"), "(No Subject)")
        sender = next((h["value"] for h in headers if h["name"] == "From"), "(Unknown Sender)")
        message_id = msg_data.get("id")

        # Extract body text
        body = ""
        if "parts" in payload:
            for part in payload["parts"]:
                if part.get("mimeType") == "text/plain":
                    data = part.get("body", {}).get("data")
                    if data:
                        body = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore").strip()
                        break
        else:
            data = payload.get("body", {}).get("data")
            if data:
                body = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore").strip()

        if body:
            print(f"📧 Subject: {subject}")
            print(f"📝 Body:\n{body}\n")
            summary = summarize(body)
            print(f"📌 Summary: {summary}")
            store_summary(message_id, sender, subject, body, summary)
            print("-" * 60)
        else:
            print(f"📧 Subject: {subject}")
            print("⚠️ No readable body found.\n" + "-" * 60)

# ✅ Run everything
if __name__ == "__main__":
    service = authenticate_gmail()
    process_emails(service)
