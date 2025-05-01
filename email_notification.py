import smtplib
from email.mime.text import MIMEText

class EmailNotification:
    def __init__(self, smtp_server, smtp_port, from_email, password):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.from_email = from_email
        self.password = password

    def send_email(self, subject, body, to_email):
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = self.from_email
        msg['To'] = to_email

        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.from_email, self.password)
                server.sendmail(self.from_email, to_email, msg.as_string())
            print(f"Email sent to {to_email}")
        except Exception as e:
            print(f"Failed to send email: {e}")

# Example usage
if __name__ == "__main__":
    email_notifier = EmailNotification('smtp.example.com', 587, 'your_email@example.com', 'your_password')
    email_notifier.send_email('Test Subject', 'This is a test email body.', 'recipient@example.com')
