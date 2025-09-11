"""
Tests for the JIRA link converter utility.
"""

from utils.utils import convert_jira_ids_to_links


def test_convert_jira_ids_to_links():
    """Test converting JIRA IDs to hyperlinks in text."""
    test_jira_server = "https://test-jira.example.com"

    test_content = """
    # Test Document
    
    This is CONSOLE-4661 and this is AGENT-1262.
    This should not match: lowercase-123
    Also matches ABC-123.
    """

    modified_content = convert_jira_ids_to_links(test_content, test_jira_server)

    # Check that the JIRA IDs were converted to links
    assert f"[CONSOLE-4661]({test_jira_server}/browse/CONSOLE-4661)" in modified_content
    assert f"[AGENT-1262]({test_jira_server}/browse/AGENT-1262)" in modified_content
    assert f"[ABC-123]({test_jira_server}/browse/ABC-123)" in modified_content
    assert "lowercase-123" in modified_content  # Should remain unchanged
