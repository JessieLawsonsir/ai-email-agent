import logging
import base64
import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import mysql.connector
from dotenv import load_dotenv

# ✅ Load environment variables from .env file
load_dotenv()

# 🔐 Gmail API scopes
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.labels"
]

# ✅ MySQL DB config from environment variables
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME")
}

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def authenticate_gmail():
    creds = None
    token_path = 'token.json'

    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        if not creds or not creds.valid or not all(scope in creds.scopes for scope in SCOPES):
            os.remove(token_path)
            return authenticate_gmail()
    else:
        flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
        creds = flow.run_local_server(port=0)
        with open(token_path, 'w') as token:
            token.write(creds.to_json())

    return build('gmail', 'v1', credentials=creds)


def detect_intent(email_body):
    body = email_body.lower()
    if "order" in body or "purchase" in body or "buy" in body:
        return "order"
    elif "complaint" in body or "problem" in body or "issue" in body:
        return "complaint"
    elif "help" in body or "question" in body or "inquiry" in body:
        return "inquiry"
    else:
        return "other"


def store_email_to_db(sender, subject, body, msg_id, intent=None):
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM emails WHERE message_id = %s", (msg_id,))
        if cursor.fetchone():
            if intent:
                cursor.execute("UPDATE emails SET intent = %s WHERE message_id = %s", (intent, msg_id))
                conn.commit()
                logging.info(f"🔄 Updated intent for message ID {msg_id} to '{intent}'")
            else:
                logging.info(f"⏩ Email already saved: {subject}")
            return

        sql = "INSERT INTO emails (sender, subject, body, message_id, intent) VALUES (%s, %s, %s, %s, %s)"
        cursor.execute(sql, (sender, subject, body, msg_id, intent))
        conn.commit()
        logging.info(f"✅ Saved email: {subject} with intent '{intent}'")

    except mysql.connector.Error as err:
        logging.error(f"❌ DB Error: {err}")
    finally:
        cursor.close()
        conn.close()


def get_unread_emails(service):
    results = service.users().messages().list(userId='me', labelIds=['INBOX'], q="is:unread").execute()
    messages = results.get('messages', [])

    logging.info(f"📨 Found {len(messages)} unread messages.")

    for msg in messages:
        msg_data = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
        payload = msg_data['payload']
        headers = payload.get('headers', [])
        msg_id = msg_data['id']

        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), "(No Subject)")
        sender = next((h['value'] for h in headers if h['name'] == 'From'), "(Unknown Sender)")

        body = ""
        parts = payload.get('parts', [])
        if parts:
            for part in parts:
                if part['mimeType'] == 'text/plain':
                    data = part['body'].get('data')
                    if data:
                        body = base64.urlsafe_b64decode(data).decode('utf-8')
                        break
        else:
            data = payload['body'].get('data')
            if data:
                body = base64.urlsafe_b64decode(data).decode('utf-8')

        intent = detect_intent(body)
        logging.info(f"Detected intent: {intent} for message ID {msg_id}")
        store_email_to_db(sender, subject, body, msg_id, intent)


if __name__ == "__main__":
    service = authenticate_gmail()
    get_unread_emails(service)
