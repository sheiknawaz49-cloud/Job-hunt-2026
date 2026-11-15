# test_mailbox_ops.py
from tools.gmail_tool import search_emails, read_email, trash_email

if __name__ == "__main__":
    print("Searching for the latest 3 emails in INBOX...")
    messages = search_emails(query="label:INBOX", max_results=3)

    if not messages:
        print("No messages found matching query.")
        exit()

    for msg_meta in messages:
        details = read_email(msg_meta["id"])
        print("\n-------------------------------------------")
        print(f"ID:      {details['id']}")
        print(f"From:    {details['from']}")
        print(f"Subject: {details['subject']}")
        print(f"Snippet: {details['snippet'][:100]}...")

    # Example of moving a message to Trash (uncomment to test):
    # target_id = messages[0]["id"]
    # print(f"\nMoving message {target_id} to Trash...")
    # trash_email(target_id)
    # print("Trashed successfully.")