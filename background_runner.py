import logging
import base64
import re
from datetime import datetime, timedelta
from apscheduler.schedulers.blocking import BlockingScheduler
from email.mime.text import MIMEText
from auth_gmail import get_gmail_service
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
import mysql.connector

# ✅ Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ✅ MySQL config
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "qwert12345",
    "database": "email_agent"
}

# ✅ Load FLAN-T5 Large
model_name = "google/flan-t5-large"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSeq2SeqLM.from_pretrained(model_name)

# ✅ Convert weekday name to date
def convert_to_date(weekday_name):
    weekdays = {
        "monday": 0, "tuesday": 1, "wednesday": 2,
        "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6
    }
    weekday_name = weekday_name.lower()
    if weekday_name not in weekdays:
        return None
    today = datetime.today()
    target = weekdays[weekday_name]
    days_ahead = (target - today.weekday() + 7) % 7 or 7
    return (today + timedelta(days=days_ahead)).strftime("%Y-%m-%d")

# ✅ Extract order info from email body
def extract_order_info(body):
    product_match = re.search(r'order(?:.*?for)?(?:\s*[:-]?\s*)(.+?)(?:\.|\n|$)', body, re.IGNORECASE)
    qty_match = re.search(r'(\d+)\s+(?:units|pieces|packs)', body)
    loc_match = re.search(r'deliver(?:y)?(?:\s*to| at)?\s+([a-zA-Z\s]+?)(?:\.|\n|by)', body, re.IGNORECASE)
    date_match = re.search(r'(by|before)\s+(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|\d{4}-\d{2}-\d{2})', body)

    product = product_match.group(1).strip() if product_match else None
    quantity = int(qty_match.group(1)) if qty_match else None
    location = loc_match.group(1).strip() if loc_match else None
    delivery_date = None

    if date_match:
        raw_date = date_match.group(2).strip()
        delivery_date = raw_date if re.match(r"\d{4}-\d{2}-\d{2}", raw_date) else convert_to_date(raw_date)

    return product, quantity, location, delivery_date

# ✅ Save full email to DB
def save_full_email(sender, subject, body, message_id):
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM emails WHERE message_id = %s", (message_id,))
        if cursor.fetchone():
            return
        cursor.execute(
            "INSERT INTO emails (sender, subject, body, message_id) VALUES (%s, %s, %s, %s)",
            (sender, subject, body, message_id)
        )
        conn.commit()
        logging.info(f"✅ Saved email: {subject}")
    except Exception as e:
        logging.error(f"❌ Error saving email: {e}")
    finally:
        cursor.close()
        conn.close()

# ✅ Save summary to DB
def save_summary(sender, subject, summary):
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO email_summaries (sender, subject, summary) VALUES (%s, %s, %s)",
            (sender, subject, summary)
        )
        conn.commit()
        logging.info(f"📝 Summary saved: {subject}")
    except Exception as e:
        logging.error(f"❌ Error saving summary: {e}")
    finally:
        cursor.close()
        conn.close()

# ✅ Save order to DB
def save_order(sender, product, quantity, location, delivery_date, message_id, ai_reply):
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM orders WHERE message_id = %s", (message_id,))
        if cursor.fetchone():
            return
        cursor.execute(
            "INSERT INTO orders (sender, product, quantity, location, delivery_date, message_id, ai_reply) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (sender, product, quantity, location, delivery_date, message_id, ai_reply)
        )
        conn.commit()
        logging.info(f"📦 Order saved: {product} x{quantity} to {location} by {delivery_date}")
    except Exception as e:
        logging.error(f"❌ Error saving order: {e}")
    finally:
        cursor.close()
        conn.close()

# ✅ Summarize using FLAN-T5
def summarize_text(text):
    input_text = "summarize: " + text.strip().replace('\n', ' ')
    inputs = tokenizer.encode(input_text, return_tensors="pt", max_length=512, truncation=True)
    outputs = model.generate(inputs, max_length=80, min_length=20, num_beams=4, length_penalty=2.0, early_stopping=True)
    return tokenizer.decode(outputs[0], skip_special_tokens=True)

# ✅ Generate smart reply using FLAN-T5
def generate_reply(email_body):
    prompt = f"""
You are a professional assistant replying to a client regarding their inquiry or order.

Email:
{email_body}

Reply with a formal, polite, and helpful response.
"""
    inputs = tokenizer.encode(prompt, return_tensors="pt", max_length=512, truncation=True)
    outputs = model.generate(
        inputs,
        max_length=180,
        min_length=60,
        do_sample=True,
        top_k=50,
        top_p=0.95,
        temperature=0.85,
        repetition_penalty=1.1
    )
    return tokenizer.decode(outputs[0], skip_special_tokens=True)

# ✅ Send smart reply
def send_reply(service, sender_email, subject, thread_id, email_body):
    try:
        generated_reply = generate_reply(email_body)

        mime_msg = MIMEText(generated_reply)
        mime_msg['to'] = sender_email
        mime_msg['subject'] = f"Re: {subject}"
        mime_msg['in-reply-to'] = thread_id
        mime_msg['references'] = thread_id

        raw_msg = {'raw': base64.urlsafe_b64encode(mime_msg.as_bytes()).decode()}
        service.users().messages().send(userId='me', body=raw_msg).execute()
        logging.info(f"📤 Smart reply sent to {sender_email}")
        return generated_reply
    except Exception as e:
        logging.error(f"❌ Failed to send smart reply: {e}")
        return None

# ✅ Main processor
def process_emails(service):
    logging.info("🔁 Checking for new emails...")

    results = service.users().messages().list(
        userId='me',
        labelIds=['INBOX'],
        q="is:unread -label:Label_1656979218593678986"
    ).execute()

    messages = results.get('messages', [])
    if not messages:
        logging.info("📬 No new messages.")
        return

    logging.info(f"📨 Found {len(messages)} unread messages.")
    for msg in messages:
        msg_id = msg['id']

        # Check if already processed
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM emails WHERE message_id = %s", (msg_id,))
        if cursor.fetchone():
            logging.info(f"⏭️ Already processed message: {msg_id}")
            cursor.close()
            conn.close()
            continue
        cursor.close()
        conn.close()

        msg_data = service.users().messages().get(userId='me', id=msg_id, format='full').execute()
        payload = msg_data['payload']
        headers = payload.get('headers', [])

        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), "(No Subject)")
        sender = next((h['value'] for h in headers if h['name'] == 'From'), "(Unknown Sender)")
        thread_id = msg_data.get('threadId')

        # Get body
        body = ""
        parts = payload.get('parts', [])
        if parts:
            for part in parts:
                if part.get('mimeType') == 'text/plain':
                    data = part['body'].get('data')
                    if data:
                        body = base64.urlsafe_b64decode(data).decode('utf-8')
                        break
        else:
            data = payload['body'].get('data')
            if data:
                body = base64.urlsafe_b64decode(data).decode('utf-8')

        save_full_email(sender, subject, body, msg_id)
        summary = summarize_text(body)
        save_summary(sender, subject, summary)

        product, quantity, location, delivery_date = extract_order_info(body)

        ai_reply = send_reply(service, sender, subject, thread_id, body)

        if product and quantity and location and delivery_date and ai_reply:
            save_order(sender, product, quantity, location, delivery_date, msg_id, ai_reply)

        # Mark as processed
        service.users().messages().modify(
            userId='me',
            id=msg_id,
            body={
                'removeLabelIds': ['UNREAD'],
                'addLabelIds': ['Label_1656979218593678986']
            }
        )
        logging.info(f"✅ Marked as processed: {subject}")

# ✅ Schedule to run every 5 seconds
def run_every_5_seconds():
    scheduler = BlockingScheduler()
    service = get_gmail_service()

    @scheduler.scheduled_job("interval", seconds=5)
    def job():
        try:
            process_emails(service)
        except Exception as e:
            logging.error(f"❌ Job error: {e}")

    logging.info("⏳ Background job started. Checking every 5 seconds.")
    scheduler.start()

# ✅ Start the agent
if __name__ == "__main__":
    run_every_5_seconds()
