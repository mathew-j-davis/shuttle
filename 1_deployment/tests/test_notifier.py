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
from shuttle.notifier import Notifier


class TestNotifier(unittest.TestCase):
    """Test cases for the Notifier class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Configure a test logger that doesn't print anything
        self.logger = logging.getLogger('test_logger')
        self.logger.setLevel(logging.CRITICAL + 1)  # Above all levels
        
        # Default test configuration
        self.notifier = Notifier(
            recipient_email="test@example.com",
            sender_email="shuttle@example.com",
            smtp_server="smtp.example.com",
            smtp_port=587,
            username="username",
            password="password",
            use_tls=True,
            logger=self.logger
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
        self.assertEqual(self.notifier.logger, self.logger)
    
    def test_notify_missing_config(self):
        """Test notifier behavior when configuration is missing."""
        notifier = Notifier(logger=self.logger)  # No email config
        result = notifier.notify("Test", "Test message")
        self.assertFalse(result)  # Should return False when config is missing
    
    @patch('smtplib.SMTP')
    def test_notify_success(self, mock_smtp):
        """Test successful notification sending."""
        # Setup the mock SMTP instance
        mock_smtp_instance = MagicMock()
        mock_smtp.return_value = mock_smtp_instance
        
        # Call notify
        result = self.notifier.notify("Test Title", "Test Message")
        
        # Verify SMTP was used correctly
        mock_smtp.assert_called_once_with("smtp.example.com", 587)
        mock_smtp_instance.starttls.assert_called_once()
        mock_smtp_instance.login.assert_called_once_with("username", "password")
        mock_smtp_instance.send_message.assert_called_once()
        mock_smtp_instance.quit.assert_called_once()
        
        # Verify result
        self.assertTrue(result)
    
    @patch('smtplib.SMTP')
    def test_notify_smtp_error(self, mock_smtp):
        """Test notification handling when SMTP error occurs."""
        # Make the SMTP connection raise an exception
        mock_smtp.side_effect = Exception("SMTP connection failed")
        
        # Call notify
        result = self.notifier.notify("Test Title", "Test Message")
        
        # Verify result
        self.assertFalse(result)


if __name__ == '__main__':
    unittest.main()
