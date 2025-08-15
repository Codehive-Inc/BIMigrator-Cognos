import unittest
import logging
import shutil
from pathlib import Path
from cognos_migrator.processors.tmdl_post_processor import TMDLPostProcessor

# Configure logging to see the output from the processor
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')

class TestTMDLPostProcessor(unittest.TestCase):

    def setUp(self):
        """Set up the test environment."""
        self.test_output_dir = Path("test_output/package_and_report_migration_output_direct")
        self.model_dir = self.test_output_dir / "pbit" / "Model"
        self.relationships_file = self.model_dir / "relationships.tmdl"
        self.backup_file = self.model_dir / "relationships.tmdl.bak"

        # Ensure the test file exists before running the test
        if not self.relationships_file.exists():
            self.fail(f"Test file not found: {self.relationships_file}")

        # Create a backup of the original file
        shutil.copy(self.relationships_file, self.backup_file)
        self.logger = logging.getLogger(__name__)

    def tearDown(self):
        """Clean up after the test."""
        # Restore the original file from backup
        if self.backup_file.exists():
            shutil.move(self.backup_file, self.relationships_file)

    def test_fix_relationships(self):
        """
        Test that the TMDLPostProcessor correctly reads, processes,
        and overwrites the relationships.tmdl file.
        """
        self.logger.info(f"--- Running test_fix_relationships on {self.relationships_file} ---")
        
        # Instantiate the processor
        post_processor = TMDLPostProcessor(logger=self.logger)

        # Run the processor
        post_processor.fix_relationships(str(self.relationships_file))

        # Verification: Read the file and check if it has been modified as expected.
        # A simple check is to see if the number of relationships has changed.
        with open(self.relationships_file, 'r') as f:
            final_content = f.read()
        
        with open(self.backup_file, 'r') as f:
            original_content = f.read()

        self.assertNotEqual(final_content, original_content, "The relationship file was not modified by the post-processor.")
        self.logger.info("Successfully verified that the relationship file was modified.")

if __name__ == '__main__':
    unittest.main() 