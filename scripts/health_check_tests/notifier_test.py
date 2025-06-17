#!/usr/bin/env python3
"""
Test script for the Shuttle Notifier class.
This script allows sending a test notification using the Notifier class directly.
"""

import sys
import os
import argparse
import logging
from pathlib import Path

# Add the parent directory to sys.path to import the notifier module
parent_dir = str(Path(__file__).resolve().parent.parent)
sys.path.append(parent_dir)

# Import the Notifier class
sys.path.append(os.path.join(parent_dir, "1_installation_steps"))
from common.notifier import Notifier

def setup_logging():
    """Set up basic logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger('notifier_test')

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Test the Shuttle Notifier')
    
    parser.add_argument('--recipient', required=True, help='Recipient email address')
    parser.add_argument('--sender', required=True, help='Sender email address')
    parser.add_argument('--smtp-server', required=True, help='SMTP server address')
    parser.add_argument('--smtp-port', type=int, required=True, help='SMTP server port')
    parser.add_argument('--username', help='SMTP authentication username')
    parser.add_argument('--password', help='SMTP authentication password')
    parser.add_argument('--no-tls', action='store_true', help='Disable TLS encryption')
    parser.add_argument('--title', default='Test Notification', help='Notification title')
    parser.add_argument('--message', default='This is a test notification from Shuttle.', 
                      help='Notification message')
    
    return parser.parse_args()

def main():
    """Main function to run the notifier test."""
    args = parse_arguments()
    logger = setup_logging('test.notifier_test')
    
    logger.info("Initializing Notifier with provided credentials")
    notifier = Notifier(
        recipient_email=args.recipient,
        sender_email=args.sender,
        smtp_server=args.smtp_server,
        smtp_port=args.smtp_port,
        username=args.username,
        password=args.password,
        use_tls=not args.no_tls
    )
    
    logger.info(f"Sending test notification with title: {args.title}")
    result = notifier.notify(args.title, args.message)
    
    if result:
        logger.info("Notification sent successfully!")
    else:
        logger.error("Failed to send notification.")
        sys.exit(1)

if __name__ == "__main__":
    main()
