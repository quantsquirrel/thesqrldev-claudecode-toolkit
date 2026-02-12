"""
Pytest configuration and shared fixtures for synod-plugin tests.
"""

import pytest


@pytest.fixture
def mock_gemini_api_key(monkeypatch):
    """Mock GEMINI_API_KEY environment variable."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key-12345")
    return "test-gemini-key-12345"


@pytest.fixture
def mock_openai_api_key(monkeypatch):
    """Mock OPENAI_API_KEY environment variable."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key-12345")
    return "test-openai-key-12345"


@pytest.fixture
def sample_valid_response():
    """Sample valid SID response with all required XML tags."""
    return """
    <confidence score="85">
        <evidence>Strong empirical data supports this conclusion</evidence>
        <logic>The reasoning follows established principles</logic>
        <expertise>Based on domain knowledge in the field</expertise>
        <can_exit>true</can_exit>
    </confidence>
    <semantic_focus>
        1. Primary focus point
        2. Secondary consideration
        3. Tertiary aspect
    </semantic_focus>
    """


@pytest.fixture
def sample_invalid_response():
    """Sample response without required SID format."""
    return "This is a plain response without any XML tags or structure."


@pytest.fixture
def sample_partial_response():
    """Sample response with only confidence tag."""
    return """
    <confidence score="70">
        <evidence>Some evidence here</evidence>
    </confidence>
    This response is missing semantic_focus tag.
    """
