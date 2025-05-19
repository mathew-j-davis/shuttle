"""
Basic tests for the shuttle_common package
"""
import unittest
from shuttle_common import __version__


class TestShuttleCommon(unittest.TestCase):
    """Basic tests for the shuttle_common package"""
    
    def test_version(self):
        """Test that version is correctly defined"""
        self.assertIsNotNone(__version__)
        self.assertTrue(len(__version__) > 0)


if __name__ == '__main__':
    unittest.main()
