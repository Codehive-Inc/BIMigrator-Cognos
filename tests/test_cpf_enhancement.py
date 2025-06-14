"""
Test CPF metadata enhancement in Power BI project generation
"""

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cognos_migrator.cpf_extractor import CPFExtractor
from cognos_migrator.migrator import CognosMigrator
from cognos_migrator.models.powerbi import PowerBIProject, DataModel, Table, Column, Relationship


class TestCPFEnhancement(unittest.TestCase):
    """Test cases for CPF metadata enhancement in Power BI projects"""

    def setUp(self):
        """Set up test fixtures"""
        # Create mock CPF extractor
        self.cpf_extractor = MagicMock(spec=CPFExtractor)
        self.setup_mock_cpf_extractor()
        
        # Create migrator with mock CPF extractor
        self.migrator = CognosMigrator(MagicMock())
        self.migrator.cpf_extractor = self.cpf_extractor
        
        # Create sample Power BI project
        self.powerbi_project = self.create_sample_powerbi_project()
    
    def setup_mock_cpf_extractor(self):
        """Set up mock CPF extractor with test data"""
        # Mock get_table_schema method
        self.cpf_extractor.get_table_schema.side_effect = self.mock_get_table_schema
        
        # Mock get_query_subject_by_id method
        self.cpf_extractor.get_query_subject_by_id.side_effect = self.mock_get_query_subject_by_id
        
        # Mock get_column_name_by_id method
        self.cpf_extractor.get_column_name_by_id.side_effect = self.mock_get_column_name_by_id
    
    def mock_get_table_schema(self, table_name):
        """Mock implementation of get_table_schema"""
        schemas = {
            'Customers': {
                'name': 'Customers',
                'id': 'QS1',
                'columns': [
                    {'name': 'CustomerID', 'id': 'C1', 'dataType': 'xs:integer', 'expression': 'Customer.ID'},
                    {'name': 'CustomerName', 'id': 'C2', 'dataType': 'xs:string', 'expression': 'Customer.Name'},
                    {'name': 'Email', 'id': 'C3', 'dataType': 'xs:string', 'expression': 'Customer.Email'}
                ],
                'relationships': [
                    {
                        'id': 'R1',
                        'name': 'CustomerOrders',
                        'sourceQuerySubjectId': 'QS1',
                        'targetQuerySubjectId': 'QS2',
                        'sourceColumns': ['C1'],
                        'targetColumns': ['C5'],
                        'cardinality': 'oneToMany'
                    }
                ]
            },
            'Orders': {
                'name': 'Orders',
                'id': 'QS2',
                'columns': [
                    {'name': 'OrderID', 'id': 'C4', 'dataType': 'xs:integer', 'expression': 'Order.ID'},
                    {'name': 'CustomerID', 'id': 'C5', 'dataType': 'xs:integer', 'expression': 'Order.CustomerID'},
                    {'name': 'OrderDate', 'id': 'C6', 'dataType': 'xs:date', 'expression': 'Order.Date'},
                    {'name': 'TotalAmount', 'id': 'C7', 'dataType': 'xs:decimal', 'expression': 'Order.Total'}
                ],
                'relationships': []
            }
        }
        return schemas.get(table_name)
    
    def mock_get_query_subject_by_id(self, query_subject_id):
        """Mock implementation of get_query_subject_by_id"""
        query_subjects = {
            'QS1': {'id': 'QS1', 'name': 'Customers'},
            'QS2': {'id': 'QS2', 'name': 'Orders'}
        }
        return query_subjects.get(query_subject_id, {})
    
    def mock_get_column_name_by_id(self, column_id):
        """Mock implementation of get_column_name_by_id"""
        column_names = {
            'C1': 'CustomerID',
            'C2': 'CustomerName',
            'C3': 'Email',
            'C4': 'OrderID',
            'C5': 'CustomerID',
            'C6': 'OrderDate',
            'C7': 'TotalAmount'
        }
        return column_names.get(column_id, '')
    
    def create_sample_powerbi_project(self):
        """Create a sample Power BI project for testing"""
        # Create data model
        data_model = DataModel()
        
        # Create Customers table
        customers_table = Table(name='Customers')
        customers_table.columns = [
            Column(name='CustomerID', data_type='Text'),
            Column(name='CustomerName', data_type='Text'),
            Column(name='Email', data_type='Text')
        ]
        
        # Create Orders table
        orders_table = Table(name='Orders')
        orders_table.columns = [
            Column(name='OrderID', data_type='Text'),
            Column(name='CustomerID', data_type='Text'),
            Column(name='OrderDate', data_type='Text'),
            Column(name='TotalAmount', data_type='Text')
        ]
        
        # Add tables to data model
        data_model.tables = [customers_table, orders_table]
        data_model.relationships = []
        
        # Create Power BI project
        powerbi_project = PowerBIProject()
        powerbi_project.data_model = data_model
        powerbi_project.metadata = {}
        
        return powerbi_project
    
    def test_enhance_with_cpf_metadata(self):
        """Test enhancing Power BI project with CPF metadata"""
        # Call the method under test
        self.migrator._enhance_with_cpf_metadata(self.powerbi_project)
        
        # Verify data types were updated
        customers_table = self.powerbi_project.data_model.tables[0]
        self.assertEqual(customers_table.columns[0].data_type, 'Int64')
        self.assertEqual(customers_table.columns[1].data_type, 'Text')
        
        orders_table = self.powerbi_project.data_model.tables[1]
        self.assertEqual(orders_table.columns[2].data_type, 'Date')
        self.assertEqual(orders_table.columns[3].data_type, 'Decimal')
        
        # Verify column descriptions were added
        self.assertEqual(customers_table.columns[0].description, 'Expression: Customer.ID')
        self.assertEqual(orders_table.columns[0].description, 'Expression: Order.ID')
        
        # Verify relationships were added
        self.assertEqual(len(self.powerbi_project.data_model.relationships), 1)
        relationship = self.powerbi_project.data_model.relationships[0]
        self.assertEqual(relationship.from_table, 'Customers')
        self.assertEqual(relationship.from_column, 'CustomerID')
        self.assertEqual(relationship.to_table, 'Orders')
        self.assertEqual(relationship.to_column, 'CustomerID')
        self.assertEqual(relationship.cardinality, 'OneToMany')
        
        # Verify metadata flag was set
        self.assertTrue(self.powerbi_project.metadata.get('cpf_metadata'))
    
    def test_enhance_with_cpf_metadata_no_extractor(self):
        """Test enhancing Power BI project with no CPF extractor"""
        # Set CPF extractor to None
        self.migrator.cpf_extractor = None
        
        # Call the method under test
        self.migrator._enhance_with_cpf_metadata(self.powerbi_project)
        
        # Verify no changes were made
        customers_table = self.powerbi_project.data_model.tables[0]
        self.assertEqual(customers_table.columns[0].data_type, 'Text')
        self.assertEqual(len(self.powerbi_project.data_model.relationships), 0)
        self.assertNotIn('cpf_metadata', self.powerbi_project.metadata)
    
    def test_map_cpf_data_type(self):
        """Test mapping CPF data types to Power BI data types"""
        test_cases = [
            ('xs:string', 'Text'),
            ('xs:integer', 'Int64'),
            ('xs:decimal', 'Decimal'),
            ('xs:double', 'Double'),
            ('xs:boolean', 'Boolean'),
            ('xs:date', 'Date'),
            ('xs:time', 'Time'),
            ('xs:dateTime', 'DateTime'),
            ('unknown_type', 'Text')  # Default case
        ]
        
        for cpf_type, expected_pbi_type in test_cases:
            with self.subTest(cpf_type=cpf_type):
                self.assertEqual(self.migrator._map_cpf_data_type(cpf_type), expected_pbi_type)
    
    def test_map_cpf_cardinality(self):
        """Test mapping CPF cardinality to Power BI cardinality"""
        test_cases = [
            ('oneToOne', 'OneToOne'),
            ('oneToMany', 'OneToMany'),
            ('manyToOne', 'ManyToOne'),
            ('manyToMany', 'ManyToMany'),
            ('unknown', 'ManyToOne')  # Default case
        ]
        
        for cpf_cardinality, expected_pbi_cardinality in test_cases:
            with self.subTest(cpf_cardinality=cpf_cardinality):
                self.assertEqual(self.migrator._map_cpf_cardinality(cpf_cardinality), expected_pbi_cardinality)
    
    def test_relationship_exists(self):
        """Test checking if a relationship already exists"""
        # Add a relationship
        rel = Relationship(
            from_table='Customers',
            from_column='CustomerID',
            to_table='Orders',
            to_column='CustomerID',
            cardinality='OneToMany'
        )
        self.powerbi_project.data_model.relationships.append(rel)
        
        # Test with existing relationship
        existing_rel = Relationship(
            from_table='Customers',
            from_column='CustomerID',
            to_table='Orders',
            to_column='CustomerID',
            cardinality='OneToMany'
        )
        self.assertTrue(self.migrator._relationship_exists(self.powerbi_project.data_model, existing_rel))
        
        # Test with non-existing relationship
        new_rel = Relationship(
            from_table='Orders',
            from_column='OrderID',
            to_table='OrderDetails',
            to_column='OrderID',
            cardinality='OneToMany'
        )
        self.assertFalse(self.migrator._relationship_exists(self.powerbi_project.data_model, new_rel))


if __name__ == '__main__':
    unittest.main()
