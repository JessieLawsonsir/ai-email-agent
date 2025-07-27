from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import mysql.connector

app = FastAPI()

# ✅ MySQL DB Configuration (Do NOT hardcode credentials in production)
DB_CONFIG = {
    "host": "localhost",
    "user": "your_db_user",          # 🔒 Replace with your actual DB user or use environment variables
    "password": "your_db_password",  # 🔒 Avoid hardcoding passwords
    "database": "email_agent"
}

@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <h2>📬 Email Reader API is Running!</h2>
    <p>Visit <a href="/emails">/emails</a> to view the latest emails from the database.</p>
    """

@app.get("/emails", response_class=HTMLResponse)
def show_emails():
    try:
        print("🔌 Connecting to MySQL...")
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()

        print("📥 Fetching emails...")
        cursor.execute("SELECT sender, subject, body FROM emails ORDER BY id DESC LIMIT 10")
        rows = cursor.fetchall()
        print(f"✅ Rows fetched: {len(rows)}")

        html = "<h2>📥 Latest Emails</h2><hr>"
        if not rows:
            html += "<p>No emails found in the database.</p>"
        else:
            for sender, subject, body in rows:
                html += f"<b>From:</b> {sender}<br>"
                html += f"<b>Subject:</b> {subject}<br>"
                html += f"<b>Body:</b><pre>{body}</pre><hr>"

        cursor.close()
        conn.close()
        return html

    except mysql.connector.Error as err:
        print(f"❌ DB Error: {err}")
        return f"<h3>❌ DB Error: {err}</h3>"
