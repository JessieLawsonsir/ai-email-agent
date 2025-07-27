import base64
import mysql.connector
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from email.mime.text import MIMEText
import logging
import os
from dotenv import load_dotenv

# ✅ Load environment variables from .env file
load_dotenv()

# ✅ MySQL DB settings from .env (no password hardcoded)
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME")
}

def insert_email_to_db(sender, subject, body):
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        query = """
            INSERT INTO emails (sender, subject, body)
            VALUES (%s, %s, %s)
        """
        cursor.execute(query, (sender, subject, body))
        conn.commit()
        cursor.close()
        conn.close()
        print("✅ Email saved to DB")
    except mysql.connector.Error as err:
        print(f"❌ DB Error: {err}")

def extract_email_details(msg_data):
    headers = msg_data['payload']['headers']
    parts = msg_data['payload'].get('parts', [])
    sender = subject = body = ""

    for header in headers:
        if header['name'] == 'From':
            sender = header['value']
        elif header['name'] == 'Subject':
            subject = header['value']

    if parts:
        for part in parts:
            mime_type = part.get('mimeType', '')
            body_data = part['body'].get('data')
            if body_data:
                decoded_text = base64.urlsafe_b64decode(body_data).decode('utf-8', errors='ignore').strip()
                if mime_type == 'text/plain' and not body:
                    body = decoded_text
                    break
                elif mime_type == 'text/html' and not body:
                    body = decoded_text

    return sender, subject, body

def generate_reply(subject, body):
    return f"""Hello,

Thank you for your email regarding "{subject}". We’ve received your message and will get back to you shortly.

Best regards,  
Client Support"""

def send_reply(service, to_email, original_subject, reply_text, thread_id):
    reply_subject = f"Re: {original_subject}"
    message = MIMEText(reply_text)
    message['to'] = to_email
    message['subject'] = reply_subject

    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
    message_body = {
        'raw': raw_message,
        'threadId': thread_id
    }

    try:
        service.users().messages().send(userId='me', body=message_body).execute()
        print(f"📩 Auto-reply sent to {to_email}")
    except Exception as e:
        print(f"❌ Failed to send reply: {e}")

def fetch_and_store_emails():
    creds = Credentials.from_authorized_user_file('token.json')
    service = build('gmail', 'v1', credentials=creds)
    results = service.users().messages().list(userId='me', labelIds=['INBOX'], q='is:unread').execute()
    messages = results.get('messages', [])

    if not messages:
        print("📭 No new unread emails.")
        return

    for msg in messages:
        msg_data = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
        thread_id = msg_data['threadId']
        sender, subject, body = extract_email_details(msg_data)
        to_email = sender.split('<')[-1].strip('>') if '<' in sender else sender

        print("\n🔹 From:", sender)
        print("🔸 Subject:", subject)
        print("📝 Body:", body[:200], "...")

        insert_email_to_db(sender, subject, body)
        reply_text = generate_reply(subject, body)
        send_reply(service, to_email, subject, reply_text, thread_id)

if __name__ == "__main__":
    fetch_and_store_emails()
