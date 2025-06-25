#!/usr/bin/env python3
"""
Unit tests for migrate_module_with_explicit_session function

This test module tests the explicit session-based module migration
functionality without using environment variables.
"""

import unittest
from unittest.mock import Mock, patch
import tempfile
import shutil
from pathlib import Path
from cognos_migrator.module_migrator import migrate_module_with_explicit_session
from cognos_migrator.client import CognosAPIError


class TestMigrateModuleWithExplicitSession(unittest.TestCase):
    """Test cases for migrate_module_with_explicit_session function"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create temporary directory for test outputs
        self.temp_dir = tempfile.mkdtemp()
        self.output_path = str(Path(self.temp_dir) / "output")
        
        # Test data
        self.cognos_url = "http://test.cognos.com/api/v1"
        self.session_key = "TEST_SESSION_KEY_12345"
        self.module_id = "i5F34A7A52E2645C0AB03C34BA50941D7"
        self.folder_id = "iFOLDER123456789"
        
        # Sample module metadata
        self.sample_module_metadata = {
            "id": self.module_id,
            "name": "Test Module",
            "defaultName": "Test Module",
            "definition": {
                "querySubjects": [
                    {
                        "id": "qs1",
                        "name": "Sales",
                        "dataItems": [
                            {
                                "name": "ProductID",
                                "dataType": "integer",
                                "identifier": "ProductID"
                            },
                            {
                                "name": "SalesAmount",
                                "dataType": "decimal",
                                "identifier": "SalesAmount"
                            }
                        ]
                    }
                ]
            }
        }
        
    def tearDown(self):
        """Clean up test fixtures"""
        if hasattr(self, 'temp_dir') and self.temp_dir:
            shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('cognos_migrator.module_migrator.CognosModuleMigratorExplicit')
    @patch('cognos_migrator.module_migrator.CognosClient.test_connection_with_session')
    @patch('cognos_migrator.module_migrator.set_task_info')
    def test_successful_migration(self, mock_set_task_info, mock_test_connection, mock_migrator_class):
        """Test successful module migration with explicit session"""
        # Set up mocks
        mock_test_connection.return_value = True
        
        # Mock migrator
        mock_migrator_instance = Mock()
        mock_migrator_instance.migrate_module.return_value = {
            'success': True,
            'module_id': self.module_id,
            'output_path': self.output_path
        }
        mock_migrator_class.return_value = mock_migrator_instance
        
        # Call the function
        result = migrate_module_with_explicit_session(
            module_id=self.module_id,
            output_path=self.output_path,
            cognos_url=self.cognos_url,
            session_key=self.session_key,
            folder_id=self.folder_id
        )
        
        # Assertions
        self.assertTrue(result)
        mock_test_connection.assert_called_once_with(self.cognos_url, self.session_key)
        mock_set_task_info.assert_called_once()
        mock_migrator_instance.migrate_module.assert_called_once_with(
            self.module_id,
            folder_id=self.folder_id,
            cpf_file_path=None
        )
    
    @patch('cognos_migrator.module_migrator.CognosClient.test_connection_with_session')
    def test_expired_session(self, mock_test_connection):
        """Test migration with expired session key"""
        # Mock expired session
        mock_test_connection.return_value = False
        
        # Call should raise CognosAPIError
        with self.assertRaises(CognosAPIError) as context:
            migrate_module_with_explicit_session(
                module_id=self.module_id,
                output_path=self.output_path,
                cognos_url=self.cognos_url,
                session_key=self.session_key
            )
        
        self.assertIn("expired or invalid", str(context.exception))
    
    @patch('cognos_migrator.module_migrator.CognosModuleMigratorExplicit')
    @patch('cognos_migrator.module_migrator.CognosClient.test_connection_with_session')
    @patch('cognos_migrator.module_migrator.set_task_info')
    def test_migration_failure(self, mock_set_task_info, mock_test_connection, mock_migrator_class):
        """Test handling of migration failure"""
        # Set up mocks
        mock_test_connection.return_value = True
        
        # Mock migrator to raise exception
        mock_migrator_instance = Mock()
        mock_migrator_instance.migrate_module.side_effect = Exception("Migration failed")
        mock_migrator_class.return_value = mock_migrator_instance
        
        # Call the function - should return False on exception
        result = migrate_module_with_explicit_session(
            module_id=self.module_id,
            output_path=self.output_path,
            cognos_url=self.cognos_url,
            session_key=self.session_key
        )
        
        # Assertions
        self.assertFalse(result)
    
    @patch('cognos_migrator.module_migrator.CognosModuleMigratorExplicit')
    @patch('cognos_migrator.module_migrator.CognosClient.test_connection_with_session')
    @patch('cognos_migrator.module_migrator.set_task_info')
    def test_with_cpf_file(self, mock_set_task_info, mock_test_connection, mock_migrator_class):
        """Test migration with CPF file path"""
        # Set up mocks
        mock_test_connection.return_value = True
        
        # Mock migrator
        mock_migrator_instance = Mock()
        mock_migrator_instance.migrate_module.return_value = {
            'success': True,
            'module_id': self.module_id
        }
        mock_migrator_class.return_value = mock_migrator_instance
        
        cpf_file_path = "/path/to/file.cpf"
        
        # Call the function with CPF file
        result = migrate_module_with_explicit_session(
            module_id=self.module_id,
            output_path=self.output_path,
            cognos_url=self.cognos_url,
            session_key=self.session_key,
            cpf_file_path=cpf_file_path
        )
        
        # Assertions
        self.assertTrue(result)
        mock_migrator_instance.migrate_module.assert_called_once_with(
            self.module_id,
            folder_id=None,
            cpf_file_path=cpf_file_path
        )
    
    @patch('cognos_migrator.module_migrator.CognosModuleMigratorExplicit')
    @patch('cognos_migrator.module_migrator.CognosClient.test_connection_with_session')
    @patch('cognos_migrator.module_migrator.set_task_info')
    def test_custom_auth_key(self, mock_set_task_info, mock_test_connection, mock_migrator_class):
        """Test migration with custom authentication header key"""
        # Set up mocks
        mock_test_connection.return_value = True
        
        # Mock migrator
        mock_migrator_instance = Mock()
        mock_migrator_instance.migrate_module.return_value = {
            'success': True,
            'module_id': self.module_id
        }
        mock_migrator_class.return_value = mock_migrator_instance
        
        custom_auth_key = "Custom-Auth-Header"
        
        # Call the function with custom auth key
        result = migrate_module_with_explicit_session(
            module_id=self.module_id,
            output_path=self.output_path,
            cognos_url=self.cognos_url,
            session_key=self.session_key,
            auth_key=custom_auth_key
        )
        
        # Assertions
        self.assertTrue(result)
        # Verify custom auth key was used
        mock_migrator_class.assert_called_once()
    
    @patch('cognos_migrator.module_migrator.CognosClient.test_connection_with_session')
    @patch('cognos_migrator.module_migrator.set_task_info')
    def test_task_id_generation(self, mock_set_task_info, mock_test_connection):
        """Test automatic task ID generation when not provided"""
        # Mock expired session to exit early
        mock_test_connection.return_value = False
        
        try:
            migrate_module_with_explicit_session(
                module_id=self.module_id,
                output_path=self.output_path,
                cognos_url=self.cognos_url,
                session_key=self.session_key
            )
        except CognosAPIError:
            pass  # Expected
        
        # Verify set_task_info was called with generated task_id
        mock_set_task_info.assert_called_once()
        task_id = mock_set_task_info.call_args[0][0]
        self.assertTrue(task_id.startswith("migration_"))
        self.assertEqual(mock_set_task_info.call_args[0][1], 12)  # total_steps
    
    @patch('cognos_migrator.module_migrator.CognosClient.test_connection_with_session')
    @patch('cognos_migrator.module_migrator.set_task_info')
    def test_provided_task_id(self, mock_set_task_info, mock_test_connection):
        """Test using provided task ID"""
        # Mock expired session to exit early
        mock_test_connection.return_value = False
        
        provided_task_id = "custom_task_123"
        
        try:
            migrate_module_with_explicit_session(
                module_id=self.module_id,
                output_path=self.output_path,
                cognos_url=self.cognos_url,
                session_key=self.session_key,
                task_id=provided_task_id
            )
        except CognosAPIError:
            pass  # Expected
        
        # Verify set_task_info was called with provided task_id
        mock_set_task_info.assert_called_once_with(provided_task_id, total_steps=12)


if __name__ == '__main__':
    unittest.main()