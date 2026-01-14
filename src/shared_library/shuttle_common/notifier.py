import smtplib
import logging
import traceback
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from .logger_injection import get_logger


class Notifier:
    """
    A class for sending notifications when important events or errors occur in Shuttle.
    This implementation supports email notifications, but can be extended for other methods.
    """
    
    def __init__(self, 
                 recipient_email=None, 
                 recipient_email_error=None,
                 recipient_email_summary=None,
                 recipient_email_hazard=None,
                 sender_email=None, 
                 smtp_server=None, 
                 smtp_port=None, 
                 username=None, 
                 password=None, 
                 use_tls=True,
                 using_simulator=False):
        """
        Initialize the notification system with recipient and sender details.
        
        Args:
            recipient_email (str): Default email address for all notifications
            recipient_email_error (str): Email address for error notifications (defaults to recipient_email)
            recipient_email_summary (str): Email address for summary notifications (defaults to recipient_email)
            recipient_email_hazard (str): Email address for hazard notifications (defaults to recipient_email)
            sender_email (str): Email address of the sender
            smtp_server (str): SMTP server address
            smtp_port (int): SMTP server port
            username (str): SMTP authentication username
            password (str): SMTP authentication password
            use_tls (bool): Whether to use TLS encryption
            using_simulator (bool): Whether running in simulator mode
        """
        self.recipient_email = recipient_email
        # Set specific email addresses with fallback to main recipient_email
        self.recipient_email_error = recipient_email_error or recipient_email
        self.recipient_email_summary = recipient_email_summary or recipient_email
        self.recipient_email_hazard = recipient_email_hazard or recipient_email
        self.sender_email = sender_email
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.use_tls = use_tls
        self.using_simulator = using_simulator

    def notify(self, title, message):
        """
        Send a notification with the given title and message to the default recipient.
        
        Args:
            title (str): The notification title
            message (str): The notification message body
            
        Returns:
            bool: True if the notification was sent successfully, False otherwise
        """

        return self._send_notification(self.recipient_email, title, message)

    def notify_error(self, title, message, exception=None):
        """
        Send an error notification to the designated error recipient.

        Args:
            title (str): The notification title
            message (str): The notification message body
            exception (Exception, optional): If provided, the full traceback will be appended to the message

        Returns:
            bool: True if the notification was sent successfully, False otherwise
        """
        if exception is not None:
            tb_str = traceback.format_exception(type(exception), exception, exception.__traceback__)
            message += "\n\n--- Stack Trace ---\n"
            message += "".join(tb_str)

        return self._send_notification(self.recipient_email_error, title, message)

    def notify_summary(self, title, message):
        """
        Send a summary notification to the designated summary recipient.
        
        Args:
            title (str): The notification title
            message (str): The notification message body
            
        Returns:
            bool: True if the notification was sent successfully, False otherwise
        """

        return self._send_notification(self.recipient_email_summary, title, message)

    def notify_hazard(self, title, message):
        """
        Send a hazard notification to the designated hazard recipient.
        
        Args:
            title (str): The notification title
            message (str): The notification message body
            
        Returns:
            bool: True if the notification was sent successfully, False otherwise
        """
        return self._send_notification(self.recipient_email_hazard, title, message)

    def _send_notification(self, recipient_email, title, message):
        """
        Internal method to send notifications to a specific recipient.
        
        Args:
            recipient_email (str): Email address to send to
            title (str): The notification title
            message (str): The notification message body
            
        Returns:
            bool: True if the notification was sent successfully, False otherwise
        """
        logger = get_logger()

        if not recipient_email or not self.smtp_server:
            logger.warning(f"Notification not sent: Missing recipient email ({recipient_email}) or SMTP server configuration")
            return False
            
        try:
            # Create a multipart message
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = recipient_email
            
            # Add simulation warning to title and message if in simulator mode
            if self.using_simulator:
                title = f"[SIMULATION MODE] {title}"
                simulator_warning = "\n\n⚠️WARNING: RUNNING IN SIMULATION MODE ⚠️\n"
                simulator_warning += "No real malware scanning is being performed!\n"
                simulator_warning += "This mode should ONLY be used for development and testing.\n\n"
                message = simulator_warning + message
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
            
            logger.info(f"Notification sent to {recipient_email}: {title}")
            return True
            
        except Exception as e:
            if logger:
                logger.error(f"Failed to send notification to {recipient_email}: {str(e)}")
            return False
