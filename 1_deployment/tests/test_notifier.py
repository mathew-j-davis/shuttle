#!/usr/bin/env python3
"""
Unit tests for the Notifier class.
"""

import unittest
from unittest.mock import patch, MagicMock
import logging
import sys
import os

# Add shuttle package to path - this makes imports work regardless of where tests are run from
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from common.notifier import Notifier


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
            use_tls=True,
            logging_options=None
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
    
    def test_notify_missing_config(self):
        """Test notifier behavior when configuration is missing."""
        notifier = Notifier(logging_options=None)  # No email config, explicitly set logging_options=None
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


if __name__ == '__main__':
    unittest.main()
