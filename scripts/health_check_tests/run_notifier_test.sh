#!/bin/bash
# Run the notifier test script with all required parameters

# Configuration for the Notifier
RECIPIENT="admin@example.com"      # Change to your actual recipient email
SENDER="shuttle@example.com"       # Change to your actual sender email
SMTP_SERVER="smtp.example.com"     # Change to your actual SMTP server
SMTP_PORT=587                      # Change to your actual SMTP port (commonly 587 for TLS)
USERNAME="smtp_username"           # Change to your actual SMTP username
PASSWORD="smtp_password"           # Change to your actual SMTP password
# Use TLS by default (omit --no-tls flag)

# Notification content
TITLE="Test Notification from Shuttle"
MESSAGE="This is a test notification sent from the Shuttle notification system at $(date). If you received this message, the notification system is working correctly."

# Run the test script with all parameters
python "$(dirname "$0")/notifier_test.py" \
  --recipient "$RECIPIENT" \
  --sender "$SENDER" \
  --smtp-server "$SMTP_SERVER" \
  --smtp-port "$SMTP_PORT" \
  --username "$USERNAME" \
  --password "$PASSWORD" \
  --title "$TITLE" \
  --message "$MESSAGE"

# Exit with the same status as the Python script
exit $?
