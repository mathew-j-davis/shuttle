#!/usr/bin/env python3
"""
Unit tests for the Notifier class.
"""

import unittest
from unittest.mock import patch, MagicMock
import logging

from shuttle_common.notifier import Notifier


class TestNotifier(unittest.TestCase):
    """Test cases for the Notifier class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Default test configuration
        self.notifier = Notifier(
            recipient_email="test@example.com",
            sender_email="shuttle@example.com",
            smtp_server="smtp.example.com",
            smtp_port=587,
            username="username",
            password="password",
            use_tls=True
        )
    
    def test_init(self):
        """Test notifier initialization."""
        self.assertEqual(self.notifier.recipient_email, "test@example.com")
        self.assertEqual(self.notifier.sender_email, "shuttle@example.com")
        self.assertEqual(self.notifier.smtp_server, "smtp.example.com")
        self.assertEqual(self.notifier.smtp_port, 587)
        self.assertEqual(self.notifier.username, "username")
        self.assertEqual(self.notifier.password, "password")
        self.assertTrue(self.notifier.use_tls)
    
    def test_init_fallback_emails(self):
        """Test that specific email addresses fallback to main recipient_email."""
        notifier = Notifier(
            recipient_email="main@example.com",
            smtp_server="smtp.example.com"
        )
        
        # All specific emails should fallback to main recipient_email
        self.assertEqual(notifier.recipient_email, "main@example.com")
        self.assertEqual(notifier.recipient_email_error, "main@example.com")
        self.assertEqual(notifier.recipient_email_summary, "main@example.com")
        self.assertEqual(notifier.recipient_email_hazard, "main@example.com")
    
    def test_init_specific_emails(self):
        """Test that specific email addresses override the fallback."""
        notifier = Notifier(
            recipient_email="main@example.com",
            recipient_email_error="errors@example.com",
            recipient_email_summary="reports@example.com",
            recipient_email_hazard="security@example.com",
            smtp_server="smtp.example.com"
        )
        
        # Each specific email should be set correctly
        self.assertEqual(notifier.recipient_email, "main@example.com")
        self.assertEqual(notifier.recipient_email_error, "errors@example.com")
        self.assertEqual(notifier.recipient_email_summary, "reports@example.com")
        self.assertEqual(notifier.recipient_email_hazard, "security@example.com")
    
    def test_init_partial_specific_emails(self):
        """Test mixed specific and fallback email configuration."""
        notifier = Notifier(
            recipient_email="main@example.com",
            recipient_email_error="errors@example.com",
            # summary and hazard should fallback to main
            smtp_server="smtp.example.com"
        )
        
        self.assertEqual(notifier.recipient_email, "main@example.com")
        self.assertEqual(notifier.recipient_email_error, "errors@example.com")
        self.assertEqual(notifier.recipient_email_summary, "main@example.com")  # fallback
        self.assertEqual(notifier.recipient_email_hazard, "main@example.com")   # fallback
    
    def test_notify_missing_config(self):
        """Test notifier behavior when configuration is missing."""
        notifier = Notifier()  # No email config
        result = notifier.notify("Test", "Test message")
        self.assertFalse(result)  # Should return False when config is missing
    
    @patch('smtplib.SMTP')
    def test_notify_success(self, mock_smtp):
        """Test successful notification sending."""
        # Setup the mock SMTP instance
        # First, create a mock object that will stand in for an actual SMTP connection object
        mock_smtp_instance = MagicMock()
        
        # Configure the mock_smtp (which is the patched smtplib.SMTP constructor)
        # to return our mock_smtp_instance whenever it's called
        # This means when code does 'smtp = smtplib.SMTP(server, port)', 
        # smtp will actually be our mock_smtp_instance object
        mock_smtp.return_value = mock_smtp_instance
        
        # Call notify
        result = self.notifier.notify("Test Title", "Test Message")
        
        # Verify SMTP was used correctly
        # Check that the SMTP constructor was called with the correct server and port
        mock_smtp.assert_called_once_with("smtp.example.com", 587)
        
        # Verify that starttls() was called exactly once (for TLS encryption)
        mock_smtp_instance.starttls.assert_called_once()
        
        # Verify that login() was called with the correct username and password
        mock_smtp_instance.login.assert_called_once_with("username", "password")
        
        # Verify that send_message() was called to send the email
        mock_smtp_instance.send_message.assert_called_once()
        
        # Verify that quit() was called to close the connection properly
        mock_smtp_instance.quit.assert_called_once()
        
        # Verify result
        self.assertTrue(result)
    
    @patch('smtplib.SMTP')
    def test_notify_smtp_error(self, mock_smtp):
        """Test notification handling when SMTP error occurs."""
        # Configure the mock_smtp constructor to raise an exception when called
        # This simulates a failure in establishing the SMTP connection
        # When the code under test calls smtplib.SMTP(), it will raise this exception
        # instead of returning a connection object
        mock_smtp.side_effect = Exception("SMTP connection failed")
        
        # Call notify
        result = self.notifier.notify("Test Title", "Test Message")
        
        # Verify result
        self.assertFalse(result)
    
    @patch('smtplib.SMTP')
    def test_notify_error_method(self, mock_smtp):
        """Test notify_error method sends to correct recipient."""
        # Create notifier with specific error email
        notifier = Notifier(
            recipient_email="main@example.com",
            recipient_email_error="errors@example.com",
            smtp_server="smtp.example.com"
        )
        
        mock_smtp_instance = MagicMock()
        mock_smtp.return_value = mock_smtp_instance
        
        # Call notify_error
        result = notifier.notify_error("Error Title", "Error Message")
        
        # Verify it used the error email address
        mock_smtp_instance.send_message.assert_called_once()
        sent_message = mock_smtp_instance.send_message.call_args[0][0]
        self.assertEqual(sent_message['To'], "errors@example.com")
        self.assertTrue(result)
    
    @patch('smtplib.SMTP')
    def test_notify_summary_method(self, mock_smtp):
        """Test notify_summary method sends to correct recipient."""
        # Create notifier with specific summary email
        notifier = Notifier(
            recipient_email="main@example.com",
            recipient_email_summary="reports@example.com",
            smtp_server="smtp.example.com"
        )
        
        mock_smtp_instance = MagicMock()
        mock_smtp.return_value = mock_smtp_instance
        
        # Call notify_summary
        result = notifier.notify_summary("Summary Title", "Summary Message")
        
        # Verify it used the summary email address
        mock_smtp_instance.send_message.assert_called_once()
        sent_message = mock_smtp_instance.send_message.call_args[0][0]
        self.assertEqual(sent_message['To'], "reports@example.com")
        self.assertTrue(result)
    
    @patch('smtplib.SMTP')
    def test_notify_hazard_method(self, mock_smtp):
        """Test notify_hazard method sends to correct recipient."""
        # Create notifier with specific hazard email
        notifier = Notifier(
            recipient_email="main@example.com",
            recipient_email_hazard="security@example.com",
            smtp_server="smtp.example.com"
        )
        
        mock_smtp_instance = MagicMock()
        mock_smtp.return_value = mock_smtp_instance
        
        # Call notify_hazard
        result = notifier.notify_hazard("Hazard Title", "Hazard Message")
        
        # Verify it used the hazard email address
        mock_smtp_instance.send_message.assert_called_once()
        sent_message = mock_smtp_instance.send_message.call_args[0][0]
        self.assertEqual(sent_message['To'], "security@example.com")
        self.assertTrue(result)
    
    @patch('smtplib.SMTP')
    def test_fallback_email_usage(self, mock_smtp):
        """Test that methods fallback to main email when specific email not set."""
        # Create notifier with only main email
        notifier = Notifier(
            recipient_email="main@example.com",
            smtp_server="smtp.example.com"
        )
        
        mock_smtp_instance = MagicMock()
        mock_smtp.return_value = mock_smtp_instance
        
        # Test all methods use fallback email
        test_cases = [
            (notifier.notify, "General"),
            (notifier.notify_error, "Error"),
            (notifier.notify_summary, "Summary"), 
            (notifier.notify_hazard, "Hazard")
        ]
        
        for method, title_prefix in test_cases:
            mock_smtp_instance.reset_mock()
            result = method(f"{title_prefix} Title", f"{title_prefix} Message")
            
            # Verify it used the main email address
            mock_smtp_instance.send_message.assert_called_once()
            sent_message = mock_smtp_instance.send_message.call_args[0][0]
            self.assertEqual(sent_message['To'], "main@example.com")
            self.assertTrue(result)
    
    def test_missing_recipient_error_logging(self):
        """Test that missing recipient email is properly logged."""
        # Create notifier without recipient email but with SMTP config
        notifier = Notifier(
            smtp_server="smtp.example.com"
        )
        
        # All methods should return False when no recipient email
        self.assertFalse(notifier.notify("Test", "Message"))
        self.assertFalse(notifier.notify_error("Test", "Message"))
        self.assertFalse(notifier.notify_summary("Test", "Message"))
        self.assertFalse(notifier.notify_hazard("Test", "Message"))


if __name__ == '__main__':
    unittest.main()
