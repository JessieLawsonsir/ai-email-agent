from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import mysql.connector
import os

app = FastAPI()

# ✅ MySQL Configuration (No hardcoded password)
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": os.getenv("MYSQL_PASSWORD"),  # 🔒 Use env var
    "database": "email_agent"
}

@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <h2>📬 Email Reader API is Running!</h2>
    <ul>
        <li><a href='/emails'>📝 View Email Summaries</a></li>
        <li><a href='/orders'>📦 View Order Requests</a></li>
    </ul>
    """

@app.get("/emails", response_class=HTMLResponse)
def show_emails():
    conn = None
    cursor = None
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SELECT sender, subject, summary FROM email_summaries ORDER BY id DESC LIMIT 10")
        rows = cursor.fetchall()

        html = "<h2>📥 Latest Email Summaries</h2><hr>"
        if not rows:
            html += "<p>No summaries found in the database.</p>"
        else:
            for sender, subject, summary in rows:
                html += f"<b>From:</b> {sender}<br>"
                html += f"<b>Subject:</b> {subject}<br>"
                html += f"<b>Summary:</b><pre>{summary}</pre><hr>"

        return html

    except mysql.connector.Error as err:
        return f"<h3>❌ DB Error: {err}</h3>"

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.get("/orders", response_class=HTMLResponse)
def show_orders():
    conn = None
    cursor = None
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT sender, product, quantity, location, delivery_date, created_at
            FROM orders ORDER BY id DESC LIMIT 10
        """)
        rows = cursor.fetchall()

        html = "<h2>📦 Latest Order Requests</h2><hr>"
        if not rows:
            html += "<p>No orders found in the database.</p>"
        else:
            for sender, product, quantity, location, delivery_date, created_at in rows:
                html += f"<b>From:</b> {sender}<br>"
                html += f"<b>Product:</b> {product}<br>"
                html += f"<b>Quantity:</b> {quantity}<br>"
                html += f"<b>Location:</b> {location}<br>"
                html += f"<b>Delivery Date:</b> {delivery_date}<br>"
                html += f"<b>Logged At:</b> {created_at}<br><hr>"

        return html

    except mysql.connector.Error as err:
        return f"<h3>❌ DB Error: {err}</h3>"

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
