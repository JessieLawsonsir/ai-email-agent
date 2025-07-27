from email_reader import authenticate_gmail

def fetch_labels():
    service = authenticate_gmail()
    results = service.users().labels().list(userId='me').execute()
    for label in results['labels']:
        print(f"{label['name']} → {label['id']}")

if __name__ == "__main__":
    fetch_labels()
