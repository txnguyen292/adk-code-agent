from pathlib import Path

import pytest

from tools.agent.file_tools import FileToolError, FileTools


def test_read_write_roundtrip(tmp_path: Path) -> None:
    tools = FileTools(tmp_path)
    tools.write_file("a/b.txt", "hello")
    assert tools.read_file("a/b.txt") == "hello"


def test_path_escape_blocked(tmp_path: Path) -> None:
    tools = FileTools(tmp_path)
    with pytest.raises(FileToolError):
        tools.read_file("../secret.txt")


def test_search_returns_matches(tmp_path: Path) -> None:
    tools = FileTools(tmp_path)
    tools.write_file("notes.txt", "alpha\nbeta\nalpha")
    matches = tools.search("alpha")
    assert len(matches) == 2
