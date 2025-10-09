import pytest
from src.knowledge_base import _require_kb_service
from sema4ai.actions import ActionError
from sema4ai_docint import DIService
from unittest.mock import Mock


def test_require_kb_service() -> None:
    # Create a mock DIService with no knowledge base service
    kbless_di_service = Mock(spec=DIService)
    kbless_di_service.knowledge_base = None

    with pytest.raises(ActionError):
        kb_service = _require_kb_service(kbless_di_service)

    # Create a mock DIService with a knowledge base service
    kb_di_service = Mock(spec=DIService)
    kb_di_service.knowledge_base = Mock()

    kb_service = _require_kb_service(kb_di_service)
    assert kb_service is not None
