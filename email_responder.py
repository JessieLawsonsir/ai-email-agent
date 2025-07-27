def send_reply(service, to_email, subject, reply_text, thread_id):
    from email.mime.text import MIMEText
    import base64

    reply_subject = f"Re: {subject}"
    message = MIMEText(reply_text)
    message['to'] = to_email
    message['subject'] = reply_subject

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    body = {
        'raw': raw,
        'threadId': thread_id
    }

    try:
        service.users().messages().send(userId='me', body=body).execute()
        print(f"📩 Reply sent to {to_email}")
    except Exception as e:
        print(f"❌ Error sending reply: {e}")
