import unittest
from core.logger import StructuredLogger

class TestStructuredLoggerSingleton(unittest.TestCase):
    def setUp(self):
        # Reset instances for clean testing
        StructuredLogger._instances.clear()

    def test_singleton_disabled_flag_updates(self):
        # 1. Create normal logger
        logger1 = StructuredLogger("test_run", disabled=False)
        self.assertFalse(logger1._disabled)

        # 2. Re-create with same name but disabled=True
        logger2 = StructuredLogger("test_run", disabled=True)
        
        # Must be the exact same object (singleton)
        self.assertIs(logger1, logger2)
        
        # But the disabled flag must be updated
        self.assertTrue(logger2._disabled)
        self.assertTrue(logger1._disabled)

    def test_singleton_different_names(self):
        logger1 = StructuredLogger("run1", disabled=False)
        logger2 = StructuredLogger("run2", disabled=True)
        
        self.assertIsNot(logger1, logger2)
        self.assertFalse(logger1._disabled)
        self.assertTrue(logger2._disabled)

if __name__ == "__main__":
    unittest.main()
