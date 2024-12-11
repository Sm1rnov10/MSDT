import pytest
from unittest.mock import patch

from main import (
    remove_extra_spaces,
    add_spaces_after_punctuation,
    fix_ellipsis,
    capitalize_sentences,
    remove_numbers,
    count_words,
    reverse_text,
    translit_to_russian,
    get_user_input
)


@pytest.mark.parametrize("input_text, expected", [
    ("   Привет,    мир!   ", "Привет, мир!"),
    ("   Hello   world   ", "Hello world")
])
def test_remove_extra_spaces(input_text, expected):
    assert remove_extra_spaces(input_text) == expected


@pytest.mark.parametrize("input_text, expected", [
    ("Привет,мир!Как дела?", "Привет, мир! Как дела?"),
    ("Hello,world!", "Hello, world!")
])
def test_add_spaces_after_punctuation(input_text, expected):
    assert add_spaces_after_punctuation(input_text) == expected


@pytest.mark.parametrize("input_text, expected", [
    ("Это просто.....", "Это просто... "),
    ("Многоточие....", "Многоточие... "),
    ("И еще.....многоточие", "И еще... многоточие")
])
def test_fix_ellipsis(input_text, expected):
    assert fix_ellipsis(input_text) == expected


@pytest.mark.parametrize("input_text, expected", [
    ("привет. как дела? всё хорошо!", "Привет. Как дела? Всё хорошо!"),
    ("hello. world? python!", "Hello. World? Python!"),
    ("this is a test. all good!",
     "This is a test. All good!")
])
def test_capitalize_sentences(input_text, expected):
    assert capitalize_sentences(input_text) == expected


@pytest.mark.parametrize("input_text, expected", [
    ("Hello123", "Hello"),
    ("123Python456", "Python"),
    ("Remove 1234 numbers", "Remove  numbers")
])
def test_remove_numbers(input_text, expected):
    assert remove_numbers(input_text) == expected


@pytest.mark.parametrize("input_text, expected", [
    ("Hello world", 2),
    ("This is a test", 4),
    ("Count these words correctly", 4)
])
def test_count_words(input_text, expected):
    assert count_words(input_text) == expected


@pytest.mark.parametrize("input_text, expected", [
    ("Hello world", "dlrow olleH"),
    ("Reverse this text", "txet siht esreveR")
])
def test_reverse_text(input_text, expected):
    assert reverse_text(input_text) == expected


@pytest.mark.parametrize("input_text, expected", [
    ("privet", "привет"),
    ("kak dela?", "как дела?"),
    ("privet mir", "привет мир")
])
def test_translit_to_russian(input_text, expected):
    assert translit_to_russian(input_text) == expected


@patch("builtins.input", side_effect=["Привет, мир!", ""])
def test_get_user_input(mock_input):
    result = get_user_input()
    assert result == "Привет, мир!"


@patch("builtins.print")
@patch("builtins.input", side_effect=["Test input", ""])
def test_integration(mock_input, mock_print):
    result = get_user_input()
    assert result == "Test input"
    mock_print.assert_called_with("Введите текст для обработки:")


@patch("builtins.input", side_effect=["privet", ""])
@patch("builtins.print")
def test_translit_integration(mock_print, mock_input):
    result = get_user_input()
    processed_result = translit_to_russian(result)
    assert processed_result == "привет"
    mock_print.assert_called_once_with("Введите текст для обработки:")