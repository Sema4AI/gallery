from unittest.mock import Mock


class TestCreateTranslationSchema:
    """Test cases for create_translation_schema action"""

    def setup_method(self):
        """Set up test fixtures"""
        self.datasource = Mock()
        self.layout_name = "test-layout"
        self.data_model_name = "test-data-model"

        # Mock layout data
        self.mock_layout = Mock()
        self.mock_layout.extraction_schema = {
            "type": "object",
            "properties": {
                "extracted_name": {"type": "string"},
                "extracted_invoice_number": {"type": "string"},
                "extracted_amount": {"type": "number"},
            },
        }
        self.mock_layout.translation_schema = None
        self.mock_layout.update = Mock()

        # Mock data model data
        self.mock_data_model = Mock()
        self.mock_data_model.model_schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "invoice_number": {"type": "string"},
                "amount": {"type": "number"},
            },
        }

        # Mock translation schema result
        self.expected_translation_schema = {
            "rules": [
                {"source": "extracted_name", "target": "name"},
                {"source": "extracted_invoice_number", "target": "invoice_number"},
                {"source": "extracted_amount", "target": "amount"},
            ]
        }
