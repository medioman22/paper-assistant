import pytest
from app.services.recommendations_service import parse_recommendations

BARE_ARRAY = """[
  {
    "title": "Support Vector Machines",
    "authors": "Cortes & Vapnik",
    "year": 1995,
    "venue": "Machine Learning",
    "relationship": "foundational",
    "takeaway": "Introduced SVMs, foundational to SVR.",
    "url": "https://doi.org/10.1007/BF00994018"
  }
]"""

MARKDOWN_FENCED = f"```json\n{BARE_ARRAY}\n```"
MARKDOWN_FENCED_NO_LANG = f"```\n{BARE_ARRAY}\n```"
PREAMBLE = f"Here are 5 related papers:\n\n{BARE_ARRAY}"
POSTAMBLE = f"{BARE_ARRAY}\n\nThese are highly relevant works."
WRAPPED_OBJECT = f'{{"recommendations": {BARE_ARRAY}}}'
WRAPPED_OTHER_KEY = f'{{"papers": {BARE_ARRAY}}}'

# Nested arrays in field values (original bug trigger)
NESTED_ARRAYS = """[
  {
    "title": "Deep Residual Learning",
    "authors": "He et al.",
    "year": 2016,
    "venue": "CVPR",
    "relationship": "foundational",
    "takeaway": "Key work on residual connections.",
    "url": "https://arxiv.org/abs/1512.03385",
    "tags": ["vision", "deep learning", "residual"]
  }
]"""

# The specific pattern that caused the original bug:
# rfind("]") landing on a nested ] instead of the outer one
MULTIPLE_NESTED = """[
  {
    "title": "Paper A",
    "authors": "Author [et al.]",
    "year": 2020,
    "venue": "NeurIPS [oral]",
    "relationship": "cited",
    "takeaway": "Relevant because of [reasons].",
    "url": "https://example.com"
  },
  {
    "title": "Paper B",
    "authors": "B et al.",
    "year": 2021,
    "venue": "ICML",
    "relationship": "parallel",
    "takeaway": "Concurrent work.",
    "url": "https://example.com/b"
  }
]"""


def _check(recs: list[dict]) -> None:
    assert isinstance(recs, list)
    assert len(recs) >= 1
    assert isinstance(recs[0], dict)
    assert "title" in recs[0]


def test_bare_array():
    _check(parse_recommendations(BARE_ARRAY))

def test_markdown_fenced_json():
    _check(parse_recommendations(MARKDOWN_FENCED))

def test_markdown_fenced_no_lang():
    _check(parse_recommendations(MARKDOWN_FENCED_NO_LANG))

def test_preamble_text():
    _check(parse_recommendations(PREAMBLE))

def test_postamble_text():
    _check(parse_recommendations(POSTAMBLE))

def test_wrapped_recommendations_key():
    _check(parse_recommendations(WRAPPED_OBJECT))

def test_wrapped_other_key():
    _check(parse_recommendations(WRAPPED_OTHER_KEY))

def test_nested_arrays_in_fields():
    recs = parse_recommendations(NESTED_ARRAYS)
    _check(recs)
    assert recs[0]["title"] == "Deep Residual Learning"

def test_brackets_in_string_fields():
    recs = parse_recommendations(MULTIPLE_NESTED)
    assert len(recs) == 2
    assert recs[0]["title"] == "Paper A"
    assert recs[1]["title"] == "Paper B"

def test_raises_on_garbage():
    with pytest.raises(ValueError, match="Could not extract"):
        parse_recommendations("Sorry, I cannot help with that.")

def test_raises_on_empty():
    with pytest.raises(ValueError):
        parse_recommendations("")
