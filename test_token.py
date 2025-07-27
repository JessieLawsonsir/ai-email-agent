# test_token.py

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

SCOPES = ['https://www.googleapis.com/auth/gmail.modify']  # Updated

def list_labels():
    creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    service = build('gmail', 'v1', credentials=creds)

    results = service.users().labels().list(userId='me').execute()
    labels = results.get('labels', [])

    print("📦 Gmail Labels:")
    for label in labels:
        print(f"{label['name']} → {label['id']}")

if __name__ == "__main__":
    list_labels()
