import pytest
from unittest.mock import Mock, patch

from sema4ai.actions import ActionError, Response
from sema4ai_docint.models import DataModel, DocumentLayout, Document

from data_model import delete_data_model_after_explicit_confirmation


class TestDeleteDataModelAfterExplicitConfirmation:
    """Test cases for delete_data_model_after_explicit_confirmation function."""

    def setup_method(self):
        """Set up test fixtures"""
        self.datasource = Mock()
        self.data_model_name = "test-data-model"
        self.normalized_name = "testdatamodel"

        # Mock data model
        self.mock_data_model = Mock()
        self.mock_data_model.name = self.normalized_name
        self.mock_data_model.description = "Test data model"
        self.mock_data_model.views = [
            {"name": "view1", "sql": "SELECT * FROM test"},
            {"name": "view2", "sql": "SELECT * FROM test2"},
        ]
        self.mock_data_model.delete = Mock(return_value=True)

        # Mock documents
        self.mock_document1 = Mock()
        self.mock_document1.id = "doc1"
        self.mock_document1.delete = Mock(return_value=True)

        self.mock_document2 = Mock()
        self.mock_document2.id = "doc2"
        self.mock_document2.delete = Mock(return_value=True)

        # Mock layouts
        self.mock_layout1 = Mock()
        self.mock_layout1.name = "layout1"
        self.mock_layout1.delete = Mock(return_value=True)

        self.mock_layout2 = Mock()
        self.mock_layout2.name = "layout2"
        self.mock_layout2.delete = Mock(return_value=True)

    def test_delete_data_model_success(self):
        """Test successful deletion of data model with all resources"""
        # Arrange
        with (
            patch.object(DataModel, "find_by_name", return_value=self.mock_data_model),
            patch.object(
                Document,
                "find_by_data_model",
                return_value=[self.mock_document1, self.mock_document2],
            ),
            patch.object(
                DocumentLayout,
                "find_by_data_model",
                return_value=[self.mock_layout1, self.mock_layout2],
            ),
            patch(
                "sema4ai_docint.models.Document.delete_by_data_model", return_value=2
            ),
            patch(
                "sema4ai_docint.models.DocumentLayout.delete_by_data_model",
                return_value=2,
            ),
            patch("data_model._drop_view") as mock_drop_view,
        ):
            # Act
            result = delete_data_model_after_explicit_confirmation(
                self.datasource, self.data_model_name, "PERMANENTLY DELETE"
            )

            # Assert
            assert isinstance(result, Response)
            assert "deleted successfully" in result.result["message"]
            assert result.result["deletion_summary"]["deleted_documents"] == 2
            assert result.result["deletion_summary"]["deleted_layouts"] == 2
            assert result.result["deletion_summary"]["deleted_views"] == 2
            assert len(result.result["deletion_summary"]["errors"]) == 0

            # Verify bulk delete methods were called
            Document.delete_by_data_model.assert_called_once_with(
                self.datasource, self.normalized_name
            )
            DocumentLayout.delete_by_data_model.assert_called_once_with(
                self.datasource, self.normalized_name
            )
            self.mock_data_model.delete.assert_called_once_with(self.datasource)
            assert mock_drop_view.call_count == 2

    def test_delete_data_model_success_no_resources(self):
        """Test successful deletion of data model with no associated resources"""
        # Arrange
        self.mock_data_model.views = []  # No views

        with (
            patch.object(DataModel, "find_by_name", return_value=self.mock_data_model),
            patch.object(Document, "find_by_data_model", return_value=[]),
            patch.object(DocumentLayout, "find_by_data_model", return_value=[]),
            patch(
                "sema4ai_docint.models.Document.delete_by_data_model", return_value=0
            ),
            patch(
                "sema4ai_docint.models.DocumentLayout.delete_by_data_model",
                return_value=0,
            ),
            patch("data_model._drop_view"),
        ):
            # Act
            result = delete_data_model_after_explicit_confirmation(
                self.datasource, self.data_model_name, "PERMANENTLY DELETE"
            )

            # Assert
            assert isinstance(result, Response)
            assert "deleted successfully" in result.result["message"]
            assert result.result["deletion_summary"]["deleted_documents"] == 0
            assert result.result["deletion_summary"]["deleted_layouts"] == 0
            assert result.result["deletion_summary"]["deleted_views"] == 0
            assert len(result.result["deletion_summary"]["errors"]) == 0

    def test_delete_data_model_insufficient_confirmation(self):
        """Test deletion fails with insufficient confirmation"""
        # Act & Assert
        with pytest.raises(ActionError) as exc_info:
            delete_data_model_after_explicit_confirmation(
                self.datasource,
                self.data_model_name,
                "DELETE",  # Wrong confirmation
            )

        assert "requires explicit confirmation" in str(exc_info.value)

    def test_delete_data_model_no_confirmation(self):
        """Test deletion fails with no confirmation"""
        # Act & Assert
        with pytest.raises(ActionError) as exc_info:
            delete_data_model_after_explicit_confirmation(
                self.datasource,
                self.data_model_name,
                "",  # Empty confirmation
            )

        assert "requires explicit confirmation" in str(exc_info.value)

    def test_delete_data_model_wrong_confirmation(self):
        """Test deletion fails with wrong confirmation text"""
        # Act & Assert
        with pytest.raises(ActionError) as exc_info:
            delete_data_model_after_explicit_confirmation(
                self.datasource,
                self.data_model_name,
                "PERMANENTLY DELETE DATA MODEL",  # Wrong confirmation
            )

        assert "requires explicit confirmation" in str(exc_info.value)

    def test_delete_data_model_case_sensitive_confirmation(self):
        """Test that confirmation is case sensitive"""
        # Act & Assert
        with pytest.raises(ActionError) as exc_info:
            delete_data_model_after_explicit_confirmation(
                self.datasource,
                self.data_model_name,
                "permanently delete",  # Wrong case
            )

        assert "requires explicit confirmation" in str(exc_info.value)

    def test_delete_data_model_not_found(self):
        """Test deletion fails when data model doesn't exist"""
        # Arrange
        with patch.object(DataModel, "find_by_name", return_value=None):
            # Act & Assert
            with pytest.raises(ActionError) as exc_info:
                delete_data_model_after_explicit_confirmation(
                    self.datasource, self.data_model_name, "PERMANENTLY DELETE"
                )

            assert "not found" in str(exc_info.value)

    def test_delete_data_model_document_deletion_fails(self):
        """Test deletion fails when document deletion fails"""
        # Arrange
        with (
            patch.object(DataModel, "find_by_name", return_value=self.mock_data_model),
            patch.object(
                Document, "find_by_data_model", return_value=[self.mock_document1]
            ),
            patch.object(DocumentLayout, "find_by_data_model", return_value=[]),
            patch(
                "sema4ai_docint.models.Document.delete_by_data_model",
                side_effect=Exception("Document deletion failed"),
            ),
            patch("data_model._drop_view"),
        ):
            # Act & Assert
            with pytest.raises(ActionError) as exc_info:
                delete_data_model_after_explicit_confirmation(
                    self.datasource, self.data_model_name, "PERMANENTLY DELETE"
                )

            assert "Failed to delete data model" in str(exc_info.value)
            assert "Error bulk deleting documents" in str(exc_info.value)

    def test_delete_data_model_layout_deletion_fails(self):
        """Test deletion fails when layout deletion fails"""
        # Arrange
        with (
            patch.object(DataModel, "find_by_name", return_value=self.mock_data_model),
            patch.object(Document, "find_by_data_model", return_value=[]),
            patch.object(
                DocumentLayout, "find_by_data_model", return_value=[self.mock_layout1]
            ),
            patch(
                "sema4ai_docint.models.DocumentLayout.delete_by_data_model",
                side_effect=Exception("Layout deletion failed"),
            ),
            patch("data_model._drop_view"),
        ):
            # Act & Assert
            with pytest.raises(ActionError) as exc_info:
                delete_data_model_after_explicit_confirmation(
                    self.datasource, self.data_model_name, "PERMANENTLY DELETE"
                )

            assert "Failed to delete data model" in str(exc_info.value)
            assert "Error bulk deleting layouts" in str(exc_info.value)

    def test_delete_data_model_view_drop_fails(self):
        """Test deletion fails when view drop fails"""
        # Arrange
        with (
            patch.object(DataModel, "find_by_name", return_value=self.mock_data_model),
            patch.object(Document, "find_by_data_model", return_value=[]),
            patch.object(DocumentLayout, "find_by_data_model", return_value=[]),
            patch("data_model._drop_view", side_effect=Exception("View drop failed")),
        ):
            # Act & Assert
            with pytest.raises(ActionError) as exc_info:
                delete_data_model_after_explicit_confirmation(
                    self.datasource, self.data_model_name, "PERMANENTLY DELETE"
                )

            assert "Failed to delete data model" in str(exc_info.value)
            assert "Error dropping view" in str(exc_info.value)

    def test_delete_data_model_data_model_deletion_fails(self):
        """Test deletion fails when data model deletion fails"""
        # Arrange
        self.mock_data_model.delete.return_value = False

        with (
            patch.object(DataModel, "find_by_name", return_value=self.mock_data_model),
            patch.object(Document, "find_by_data_model", return_value=[]),
            patch.object(DocumentLayout, "find_by_data_model", return_value=[]),
            patch("data_model._drop_view"),
        ):
            # Act & Assert
            with pytest.raises(ActionError) as exc_info:
                delete_data_model_after_explicit_confirmation(
                    self.datasource, self.data_model_name, "PERMANENTLY DELETE"
                )

            assert "Failed to delete data model" in str(exc_info.value)

    def test_delete_data_model_name_normalization(self):
        """Test that data model name is properly normalized"""
        # Arrange
        with (
            patch.object(DataModel, "find_by_name", return_value=self.mock_data_model),
            patch.object(Document, "find_by_data_model", return_value=[]),
            patch.object(DocumentLayout, "find_by_data_model", return_value=[]),
            patch("data_model._drop_view"),
        ):
            # Act
            result = delete_data_model_after_explicit_confirmation(
                self.datasource,
                "Test Data Model!@#",  # Name with special characters
                "PERMANENTLY DELETE",
            )

            # Assert
            assert isinstance(result, Response)
            # Verify find_by_name was called with normalized name
            DataModel.find_by_name.assert_called_with(
                self.datasource, "test_data_model"
            )
