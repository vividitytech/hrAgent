EMAIL_ADDRESS = "newhorizontalinc@gmail.com"#"your_email@gmail.com"
EMAIL_PASSWORD = "YOUR_GMAIL_API_PASSWORD"# "your_password" # Or your App Password

SMTP_SERVER = "smtp.gmail.com" #"your_smtp_server"  # Your SMTP Server details, for Gmail it's smtp.gmail.com
SMTP_PORT = 587  # Your SMTP Port, for Gmail it's 587
IMAP_SERVER = "imap.gmail.com" #"your_imap_server"  # Your IMAP Server, for Gmail it's imap.gmail.com
IMAP_PORT = 993  # Your IMAP Port, for Gmail it's 993

# Define the target timezone
TARGET_TIMEZONE = 'America/Los_Angeles'  # Example Los Angeles

MEETING_REQUEST_SUBJECT = "Meeting Availability Request"

# Calendar API
SCOPES = ['https://www.googleapis.com/auth/calendar']#.readonly']
SERVICE_ACCOUNT_FILE = 'apptest-35403-c3944a05a142.json'  # Replace the location or set to environment
