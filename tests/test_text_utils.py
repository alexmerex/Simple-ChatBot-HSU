from chatbot_hsu.text_utils import normalize_text, strip_vietnamese_accents


def test_strip_vietnamese_accents():
    assert strip_vietnamese_accents("Đại học Hoa Sen") == "Dai hoc Hoa Sen"


def test_normalize_text_handles_punctuation_and_spaces():
    text = "  Đại học,   Hoa Sen!!!  "
    assert normalize_text(text, fold_accents=True) == "dai hoc hoa sen"
