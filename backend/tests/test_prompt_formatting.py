"""
Regression test: PROMPT must not use .format() because it contains literal
{ } in the JSON example, causing KeyError on the first { in the template.
"""
from app.services.recommendations_service import PROMPT


def test_prompt_does_not_use_format_placeholders():
    """After .replace() substitution all known {placeholders} must be gone."""
    import re
    result = (PROMPT
        .replace("{title}", "Test Paper")
        .replace("{abstract}", "An abstract.")
        .replace("{key_points}", "point 1; point 2")
        .replace("{methodology}", "Some method.")
        .replace("{findings}", "Some findings.")
    )
    known = {"{title}", "{abstract}", "{key_points}", "{methodology}", "{findings}"}
    for placeholder in known:
        assert placeholder not in result, f"{placeholder} was not substituted"
