from query import _references_allowed_view


class TestReferencesAllowedView:
    """Test cases for _references_allowed_view function.

    Note: All queries must use qualified view names (document_intelligence.view_name)
    as required by the NL-to-SQL prompt instructions.
    """

    def test_qualified_view_name(self):
        sql_query = "SELECT * FROM document_intelligence.my_view WHERE id = 1"
        views = [{"name": "my_view"}]
        assert _references_allowed_view(sql_query, views) is True

    def test_qualified_view_name_with_newline(self):
        sql_query = """SELECT *
FROM
document_intelligence.my_view
WHERE id = 1"""
        views = [{"name": "my_view"}]
        assert _references_allowed_view(sql_query, views) is True

    def test_qualified_view_name_with_underscores(self):
        sql_query = (
            "SELECT * FROM document_intelligence.my_complex_view_name WHERE id = 1"
        )
        views = [{"name": "my_complex_view_name"}]
        assert _references_allowed_view(sql_query, views) is True

    def test_unqualified_view_name_not_allowed(self):
        sql_query = "SELECT * FROM my_view WHERE id = 1"
        views = [{"name": "my_view"}]
        # Unqualified view names should NOT match
        assert _references_allowed_view(sql_query, views) is False

    def test_qualified_view_name_prefix_no_false_positive(self):
        sql_query = "SELECT * FROM document_intelligence.my_view_extended WHERE id = 1"
        views = [{"name": "my_view"}]  # Should NOT match "my_view_extended"
        assert _references_allowed_view(sql_query, views) is False

    def test_multiple_views_one_matches(self):
        sql_query = "SELECT * FROM document_intelligence.view_two WHERE id = 1"
        views = [
            {"name": "view_one"},
            {"name": "view_two"},
            {"name": "view_three"},
        ]
        assert _references_allowed_view(sql_query, views) is True

    def test_no_matching_views(self):
        sql_query = "SELECT * FROM document_intelligence.unknown_view WHERE id = 1"
        views = [{"name": "my_view"}, {"name": "other_view"}]
        assert _references_allowed_view(sql_query, views) is False

    def test_case_insensitive_matching(self):
        sql_query = "SELECT * FROM document_intelligence.MY_VIEW WHERE id = 1"
        views = [{"name": "my_view"}]
        assert _references_allowed_view(sql_query, views) is True

    def test_view_with_join(self):
        sql_query = """
SELECT *
FROM document_intelligence.view_one v1
JOIN document_intelligence.view_two v2 ON v1.id = v2.id
"""
        views = [{"name": "view_one"}, {"name": "view_two"}]
        assert _references_allowed_view(sql_query, views) is True

    def test_qualified_view_with_multiple_whitespace_and_newline(self):
        sql_query = """SELECT *
FROM

document_intelligence.my_view
WHERE id = 1"""
        views = [{"name": "my_view"}]
        assert _references_allowed_view(sql_query, views) is True

    def test_special_characters_in_view_name(self):
        # This tests that re.escape() is being used properly
        sql_query = "SELECT * FROM document_intelligence.my_view_123 WHERE id = 1"
        views = [{"name": "my_view_123"}]
        assert _references_allowed_view(sql_query, views) is True
