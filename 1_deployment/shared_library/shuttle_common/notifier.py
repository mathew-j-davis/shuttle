import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from .logging_setup import (
    LoggingOptions,
    setup_logging
)


class Notifier:
    """
    A class for sending notifications when important events or errors occur in Shuttle.
    This implementation supports email notifications, but can be extended for other methods.
    """
    
    def __init__(self, 
                 recipient_email=None, 
                 sender_email=None, 
                 smtp_server=None, 
                 smtp_port=None, 
                 username=None, 
                 password=None, 
                 use_tls=True,
                 logging_options=None):
        """
        Initialize the notification system with recipient and sender details.
        
        Args:
            recipient_email (str): Email address of the recipient
            sender_email (str): Email address of the sender
            smtp_server (str): SMTP server address
            smtp_port (int): SMTP server port
            username (str): SMTP authentication username
            password (str): SMTP authentication password
            use_tls (bool): Whether to use TLS encryption
            logging_options (LoggingOptions): Logger properties to use for logging
        """
        self.recipient_email = recipient_email
        self.sender_email = sender_email
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.use_tls = use_tls
        self.logger = setup_logging('shuttle.common.notifier', logging_options)

    def notify(self, title, message):
        """
        Send a notification with the given title and message.
        
        Args:
            title (str): The notification title
            message (str): The notification message body
            logging_options (LoggingOptions): Logger properties to use for logging
            
        Returns:
            bool: True if the notification was sent successfully, False otherwise
        """
        

        if not self.recipient_email or not self.smtp_server:
            self.logger.warning("Notification not sent: Missing recipient email or SMTP server configuration")
            return False
            
        try:
            # Create a multipart message
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = self.recipient_email
            msg['Subject'] = f"Shuttle Notification: {title}"
            
            # Add message body
            msg.attach(MIMEText(message, 'plain'))
            
            # Connect to SMTP server
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            if self.use_tls:
                server.starttls()
            
            # Login if credentials provided
            if self.username and self.password:
                server.login(self.username, self.password)
            
            # Send email
            server.send_message(msg)
            server.quit()
            
            self.logger.info(f"Notification sent: {title}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send notification: {str(e)}")
            return False
