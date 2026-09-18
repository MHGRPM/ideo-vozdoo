import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from clipboard_paste import paste_text


@patch("clipboard_paste.pkb.Controller")
@patch("clipboard_paste.pyperclip")
def test_paste_text_copies_and_pastes(mock_pyperclip, mock_controller_cls):
    mock_pyperclip.paste.return_value = "portapapeles anterior"
    controller = MagicMock()
    mock_controller_cls.return_value = controller

    paste_text("hola mundo", auto_paste=True)

    mock_pyperclip.copy.assert_called_once_with("hola mundo")
    controller.press.assert_called_once_with("v")
    controller.release.assert_called_once_with("v")


@patch("clipboard_paste.pkb.Controller")
@patch("clipboard_paste.pyperclip")
def test_paste_text_no_auto_paste_only_copies(mock_pyperclip, mock_controller_cls):
    mock_pyperclip.paste.return_value = ""

    paste_text("solo copiar", auto_paste=False)

    mock_pyperclip.copy.assert_called_once_with("solo copiar")
    mock_controller_cls.assert_not_called()


@patch("clipboard_paste.pkb.Controller")
@patch("clipboard_paste.pyperclip")
def test_paste_text_restores_previous_clipboard(mock_pyperclip, mock_controller_cls):
    mock_pyperclip.paste.return_value = "lo que hubiera antes"
    mock_controller_cls.return_value = MagicMock()

    paste_text("nuevo texto", auto_paste=True)
    time.sleep(0.7)  # el restore corre en un hilo con time.sleep(0.5)

    assert mock_pyperclip.copy.call_args_list[-1].args == ("lo que hubiera antes",)
