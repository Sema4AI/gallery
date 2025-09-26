import pytest
from unittest.mock import Mock, patch

from validation import _regenerate_quality_checks


class TestRegenerateQualityChecks:
    """Test cases for regenerate_quality_checks function."""

    @patch("validation.DataModel.find_by_name")
    @patch("validation.AgentServerClient")
    def test_regenerate_quality_checks_success(
        self, mock_client_class, mock_find_by_name
    ):
        """Test successful regeneration of quality checks."""
        # Mock data model with existing quality checks
        mock_data_model = Mock()
        mock_data_model.quality_checks = [
            {
                "rule_name": "test_rule_1",
                "rule_description": "Check if document exists",
                "sql_query": "SELECT COUNT(*) > 0 as is_valid FROM old_view WHERE document_id = $document_id",
            },
            {
                "rule_name": "test_rule_2",
                "rule_description": "Check if required field is not null",
                "sql_query": "SELECT field_value IS NOT NULL as is_valid FROM old_view WHERE document_id = $document_id",
            },
        ]
        mock_data_model.views = [
            {
                "name": "new_view",
                "sql": "SELECT * FROM new_table",
                "columns": ["id", "name"],
            }
        ]
        mock_data_model.description = "Test data model"
        mock_find_by_name.return_value = mock_data_model

        # Mock the AgentServerClient
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        # Note: regeneration is one-for-one with limit_count=1; each call returns a single rule.
        mock_client.generate_validation_rules.side_effect = [
            [
                {
                    "rule_name": "new_rule_1",
                    "rule_description": "Check if document exists",
                    "sql_query": "SELECT COUNT(*) > 0 as is_valid FROM new_view WHERE document_id = $document_id",
                }
            ],
            [
                {
                    "rule_name": "new_rule_2",
                    "rule_description": "Check if required field is not null",
                    "sql_query": "SELECT field_value IS NOT NULL as is_valid FROM new_view WHERE document_id = $document_id",
                }
            ],
        ]

        # Mock the _store_validation_rules function
        with patch("validation._store_validation_rules") as mock_store:
            result = _regenerate_quality_checks("test_model", Mock())

            assert isinstance(result, dict)
            assert result["Message"] == "Quality checks regenerated successfully"
            assert result["RegeneratedCount"] == 2

            # Verify that all rules were replaced with newly generated ones
            updated_rules = result["Rules"]
            assert len(updated_rules) == 2
            assert updated_rules[0]["rule_name"] == "new_rule_1"
            assert updated_rules[0]["rule_description"] == "Check if document exists"
            assert "new_view" in updated_rules[0]["sql_query"]
            assert updated_rules[1]["rule_name"] == "new_rule_2"
            assert (
                updated_rules[1]["rule_description"]
                == "Check if required field is not null"
            )
            assert "new_view" in updated_rules[1]["sql_query"]

            # Verify that _store_validation_rules was called
            mock_store.assert_called_once()

    @patch("validation.DataModel.find_by_name")
    def test_regenerate_quality_checks_no_data_model(self, mock_find_by_name):
        """Test regeneration when data model is not found."""
        mock_find_by_name.return_value = None

        with pytest.raises(
            ValueError, match="Data model with name test_model not found"
        ):
            _regenerate_quality_checks("test_model", Mock())

    @patch("validation.DataModel.find_by_name")
    def test_regenerate_quality_checks_no_existing_checks(self, mock_find_by_name):
        """Test regeneration when no existing quality checks are found."""
        mock_data_model = Mock()
        mock_data_model.quality_checks = None
        mock_data_model.views = [
            {"name": "view", "sql": "SELECT * FROM table", "columns": ["id"]}
        ]
        mock_find_by_name.return_value = mock_data_model

        result = _regenerate_quality_checks("test_model", Mock())

        assert isinstance(result, dict)
        assert (
            result["Message"]
            == "No existing quality checks found for data model. Use generate_quality_checks to create new ones."
        )
        assert result["Rules"] == []
        assert result["RegeneratedCount"] == 0

    @patch("validation.DataModel.find_by_name")
    def test_regenerate_quality_checks_no_views(self, mock_find_by_name):
        """Test regeneration when no views are found."""
        mock_data_model = Mock()
        mock_data_model.quality_checks = [
            {"rule_name": "test", "rule_description": "test", "sql_query": "test"}
        ]
        mock_data_model.views = None
        mock_find_by_name.return_value = mock_data_model

        with pytest.raises(
            ValueError, match="No views found for data model test_model"
        ):
            _regenerate_quality_checks("test_model", Mock())

    @patch("validation.DataModel.find_by_name")
    @patch("validation.AgentServerClient")
    def test_regenerate_quality_checks_generation_failure(
        self, mock_client_class, mock_find_by_name
    ):
        """Test regeneration when the LLM generation fails."""
        mock_data_model = Mock()
        mock_data_model.quality_checks = [
            {
                "rule_name": "test_rule",
                "rule_description": "Test rule",
                "sql_query": "SELECT true as is_valid",
            }
        ]
        mock_data_model.views = [
            {"name": "view", "sql": "SELECT * FROM table", "columns": ["id"]}
        ]
        mock_data_model.description = "Test model"
        mock_find_by_name.return_value = mock_data_model

        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.generate_validation_rules.side_effect = Exception(
            "Generation failed"
        )

        with pytest.raises(ValueError, match="Failed to regenerate validation rules"):
            _regenerate_quality_checks("test_model", Mock())

    @patch("validation.DataModel.find_by_name")
    @patch("validation.AgentServerClient")
    def test_regenerate_quality_checks_more_new_rules(
        self, mock_client_class, mock_find_by_name
    ):
        """Test regeneration when more new rules are generated than existing ones."""
        mock_data_model = Mock()
        mock_data_model.quality_checks = [
            {
                "rule_name": "existing_rule",
                "rule_description": "Existing rule",
                "sql_query": "SELECT true as is_valid",
            }
        ]
        mock_data_model.views = [
            {"name": "view", "sql": "SELECT * FROM table", "columns": ["id"]}
        ]
        mock_data_model.description = "Test model"
        mock_find_by_name.return_value = mock_data_model

        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.generate_validation_rules.return_value = [
            {
                "rule_name": "new_rule_1",
                "rule_description": "New rule 1",
                "sql_query": "SELECT true as is_valid FROM new_view",
            },
            {
                "rule_name": "new_rule_2",
                "rule_description": "New rule 2",
                "sql_query": "SELECT false as is_valid FROM new_view",
            },
        ]

        with patch("validation._store_validation_rules") as mock_store:
            result = _regenerate_quality_checks("test_model", Mock())

            # Note: regeneration is one-for-one with limit_count=1; only the first generated rule is used.
            assert result["RegeneratedCount"] == 1
            updated_rules = result["Rules"]
            assert len(updated_rules) == 1

            # The single existing rule should be replaced with the first newly generated one
            assert updated_rules[0]["rule_name"] == "new_rule_1"
            assert updated_rules[0]["rule_description"] == "New rule 1"
            # Verify that _store_validation_rules was called
            mock_store.assert_called_once()
