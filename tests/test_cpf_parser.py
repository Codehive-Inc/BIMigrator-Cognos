"""
Unit tests for CPF Parser module
"""

import os
import sys
import unittest
from pathlib import Path
import json

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cognos_migrator.cpf_parser import CPFParser
from cognos_migrator.cpf_extractor import CPFExtractor


class TestCPFParser(unittest.TestCase):
    """Test cases for CPF Parser"""

    def setUp(self):
        """Set up test fixtures"""
        # Path to test CPF file
        self.test_cpf_path = Path(__file__).parent / "fixtures" / "test_model.cpf"
        
        # Create fixtures directory if it doesn't exist
        fixtures_dir = Path(__file__).parent / "fixtures"
        fixtures_dir.mkdir(exist_ok=True)
        
        # Create a minimal test CPF file if it doesn't exist
        if not self.test_cpf_path.exists():
            self._create_test_cpf_file()
    
    def _create_test_cpf_file(self):
        """Create a minimal test CPF file for testing"""
        minimal_cpf_content = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://www.developer.cognos.com/schemas/cpf/1/">
    <dataSources>
        <dataSource id="DS1" name="TestDataSource">
            <connectionProperties>
                <connectionProperty name="type" value="JDBC"/>
                <connectionProperty name="jdbcURL" value="jdbc:sqlserver://test-server:1433;databaseName=TestDB"/>
            </connectionProperties>
        </dataSource>
    </dataSources>
    <namespace id="NS1" name="TestNamespace">
        <querySubject id="QS1" name="Customers">
            <column id="C1" name="CustomerID" dataType="xs:integer"/>
            <column id="C2" name="CustomerName" dataType="xs:string"/>
            <column id="C3" name="Email" dataType="xs:string"/>
        </querySubject>
        <querySubject id="QS2" name="Orders">
            <column id="C4" name="OrderID" dataType="xs:integer"/>
            <column id="C5" name="CustomerID" dataType="xs:integer"/>
            <column id="C6" name="OrderDate" dataType="xs:date"/>
            <column id="C7" name="TotalAmount" dataType="xs:decimal"/>
        </querySubject>
        <relationship id="R1" name="CustomerOrders">
            <sourceQuerySubject refId="QS1"/>
            <targetQuerySubject refId="QS2"/>
            <sourceColumn refId="C1"/>
            <targetColumn refId="C5"/>
            <cardinality>oneToMany</cardinality>
        </relationship>
    </namespace>
</project>
"""
        with open(self.test_cpf_path, 'w', encoding='utf-8') as f:
            f.write(minimal_cpf_content)

    def test_cpf_parser_initialization(self):
        """Test CPF Parser initialization"""
        parser = CPFParser(self.test_cpf_path)
        self.assertIsNotNone(parser)
        self.assertEqual(str(parser.cpf_path), str(self.test_cpf_path))
    
    def test_extract_data_sources(self):
        """Test extraction of data sources"""
        parser = CPFParser(self.test_cpf_path)
        data_sources = parser.extract_data_sources()
        
        self.assertIsNotNone(data_sources)
        self.assertEqual(len(data_sources), 1)
        self.assertEqual(data_sources[0]['id'], 'DS1')
        self.assertEqual(data_sources[0]['name'], 'TestDataSource')
        self.assertEqual(data_sources[0]['type'], 'JDBC')
    
    def test_extract_query_subjects(self):
        """Test extraction of query subjects"""
        parser = CPFParser(self.test_cpf_path)
        query_subjects = parser.extract_query_subjects()
        
        self.assertIsNotNone(query_subjects)
        self.assertEqual(len(query_subjects), 2)
        
        # Check first query subject
        self.assertEqual(query_subjects[0]['id'], 'QS1')
        self.assertEqual(query_subjects[0]['name'], 'Customers')
        self.assertEqual(len(query_subjects[0]['columns']), 3)
        
        # Check second query subject
        self.assertEqual(query_subjects[1]['id'], 'QS2')
        self.assertEqual(query_subjects[1]['name'], 'Orders')
        self.assertEqual(len(query_subjects[1]['columns']), 4)
    
    def test_extract_relationships(self):
        """Test extraction of relationships"""
        parser = CPFParser(self.test_cpf_path)
        relationships = parser.extract_relationships()
        
        self.assertIsNotNone(relationships)
        self.assertEqual(len(relationships), 1)
        self.assertEqual(relationships[0]['id'], 'R1')
        self.assertEqual(relationships[0]['name'], 'CustomerOrders')
        self.assertEqual(relationships[0]['sourceQuerySubjectId'], 'QS1')
        self.assertEqual(relationships[0]['targetQuerySubjectId'], 'QS2')
        self.assertEqual(relationships[0]['sourceColumns'], ['C1'])
        self.assertEqual(relationships[0]['targetColumns'], ['C5'])
        self.assertEqual(relationships[0]['cardinality'], 'oneToMany')
    
    def test_extract_all(self):
        """Test extraction of all metadata"""
        parser = CPFParser(self.test_cpf_path)
        metadata = parser.extract_all()
        
        self.assertIsNotNone(metadata)
        self.assertIn('dataSources', metadata)
        self.assertIn('querySubjects', metadata)
        self.assertIn('relationships', metadata)
        self.assertIn('namespaces', metadata)
    
    def test_save_as_json(self):
        """Test saving metadata as JSON"""
        parser = CPFParser(self.test_cpf_path)
        output_path = Path(__file__).parent / "fixtures" / "test_output.json"
        
        parser.save_as_json(output_path)
        self.assertTrue(output_path.exists())
        
        # Load and verify JSON content
        with open(output_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        self.assertIn('dataSources', metadata)
        self.assertIn('querySubjects', metadata)
        self.assertIn('relationships', metadata)
        self.assertIn('namespaces', metadata)
        
        # Clean up
        output_path.unlink(missing_ok=True)


class TestCPFExtractor(unittest.TestCase):
    """Test cases for CPF Extractor"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Path to test CPF file
        self.test_cpf_path = Path(__file__).parent / "fixtures" / "test_model.cpf"
        
        # Create fixtures directory if it doesn't exist
        fixtures_dir = Path(__file__).parent / "fixtures"
        fixtures_dir.mkdir(exist_ok=True)
        
        # Create a minimal test CPF file if it doesn't exist
        if not self.test_cpf_path.exists():
            self._create_test_cpf_file()
        
        # Initialize extractor
        self.extractor = CPFExtractor(self.test_cpf_path)
    
    def _create_test_cpf_file(self):
        """Create a minimal test CPF file for testing"""
        minimal_cpf_content = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://www.developer.cognos.com/schemas/cpf/1/">
    <dataSources>
        <dataSource id="DS1" name="TestDataSource">
            <connectionProperties>
                <connectionProperty name="type" value="JDBC"/>
                <connectionProperty name="jdbcURL" value="jdbc:sqlserver://test-server:1433;databaseName=TestDB"/>
            </connectionProperties>
        </dataSource>
    </dataSources>
    <namespace id="NS1" name="TestNamespace">
        <querySubject id="QS1" name="Customers">
            <column id="C1" name="CustomerID" dataType="xs:integer"/>
            <column id="C2" name="CustomerName" dataType="xs:string"/>
            <column id="C3" name="Email" dataType="xs:string"/>
        </querySubject>
        <querySubject id="QS2" name="Orders">
            <column id="C4" name="OrderID" dataType="xs:integer"/>
            <column id="C5" name="CustomerID" dataType="xs:integer"/>
            <column id="C6" name="OrderDate" dataType="xs:date"/>
            <column id="C7" name="TotalAmount" dataType="xs:decimal"/>
        </querySubject>
        <relationship id="R1" name="CustomerOrders">
            <sourceQuerySubject refId="QS1"/>
            <targetQuerySubject refId="QS2"/>
            <sourceColumn refId="C1"/>
            <targetColumn refId="C5"/>
            <cardinality>oneToMany</cardinality>
        </relationship>
    </namespace>
</project>
"""
        with open(self.test_cpf_path, 'w', encoding='utf-8') as f:
            f.write(minimal_cpf_content)
    
    def test_get_data_sources(self):
        """Test getting data sources"""
        data_sources = self.extractor.get_data_sources()
        self.assertIsNotNone(data_sources)
        self.assertEqual(len(data_sources), 1)
        self.assertEqual(data_sources[0]['name'], 'TestDataSource')
    
    def test_get_query_subject_by_name(self):
        """Test getting query subject by name"""
        query_subject = self.extractor.get_query_subject_by_name('Customers')
        self.assertIsNotNone(query_subject)
        self.assertEqual(query_subject['id'], 'QS1')
        self.assertEqual(query_subject['name'], 'Customers')
    
    def test_get_query_subject_by_id(self):
        """Test getting query subject by ID"""
        query_subject = self.extractor.get_query_subject_by_id('QS2')
        self.assertIsNotNone(query_subject)
        self.assertEqual(query_subject['id'], 'QS2')
        self.assertEqual(query_subject['name'], 'Orders')
    
    def test_get_related_query_subjects(self):
        """Test getting related query subjects"""
        related = self.extractor.get_related_query_subjects('QS1')
        self.assertIsNotNone(related)
        self.assertEqual(len(related), 1)
        self.assertEqual(related[0]['id'], 'QS2')
        self.assertEqual(related[0]['name'], 'Orders')
    
    def test_get_table_schema(self):
        """Test getting table schema"""
        schema = self.extractor.get_table_schema('Customers')
        self.assertIsNotNone(schema)
        self.assertEqual(schema['name'], 'Customers')
        self.assertEqual(len(schema['columns']), 3)
        self.assertEqual(len(schema['relationships']), 1)
    
    def test_get_column_name_by_id(self):
        """Test getting column name by ID"""
        column_name = self.extractor.get_column_name_by_id('C1')
        self.assertEqual(column_name, 'CustomerID')
    
    def test_generate_m_query_context(self):
        """Test generating M-query context"""
        context = self.extractor.generate_m_query_context('Customers')
        self.assertIsNotNone(context)
        self.assertIn('table_name', context)
        self.assertIn('columns', context)
        self.assertIn('relationships', context)
        self.assertEqual(context['table_name'], 'Customers')


if __name__ == '__main__':
    unittest.main()
