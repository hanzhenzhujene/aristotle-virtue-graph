from ethics_prompt_rewrite.student import parse_binary_label


def test_parse_binary_label_accepts_exact_digits() -> None:
    assert parse_binary_label("0") == 0
    assert parse_binary_label("1") == 1
    assert parse_binary_label(" 0\n") == 0


def test_parse_binary_label_rejects_other_outputs() -> None:
    assert parse_binary_label("2") is None
    assert parse_binary_label("0 because") is None
    assert parse_binary_label("") is None
