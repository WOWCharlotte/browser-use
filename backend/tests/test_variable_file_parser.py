"""
Tests for VariableFileParser.

No DB or external dependencies — pure unit tests on the parser logic.
"""

import csv
import io

import openpyxl
import pytest
from app.services.variable_file_parser import VariableFileParser, _get_extension


@pytest.fixture
def parser():
    return VariableFileParser()


# ── _get_extension ────────────────────────────────────────────────────────────

def test_get_extension_csv():
    assert _get_extension("data.csv") == ".csv"


def test_get_extension_xlsx():
    assert _get_extension("data.xlsx") == ".xlsx"


def test_get_extension_uppercase():
    assert _get_extension("DATA.CSV") == ".csv"


def test_get_extension_no_dot():
    assert _get_extension("noextension") == ""


# ── is_supported ──────────────────────────────────────────────────────────────

def test_is_supported_csv(parser):
    assert parser.is_supported("vars.csv") is True


def test_is_supported_xlsx(parser):
    assert parser.is_supported("vars.xlsx") is True


def test_is_supported_xls(parser):
    assert parser.is_supported("vars.xls") is True


def test_is_supported_txt(parser):
    assert parser.is_supported("vars.txt") is False


def test_is_supported_md(parser):
    assert parser.is_supported("vars.md") is False


# ── CSV parsing ───────────────────────────────────────────────────────────────

def _make_csv(rows: list[list[str]]) -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf)
    for row in rows:
        writer.writerow(row)
    return buf.getvalue().encode("utf-8")


def test_parse_csv_basic(parser):
    content = _make_csv([
        ["user_phone", "sms_code"],
        ["13800138001", "123456"],
        ["13900139002", "654321"],
    ])
    result = parser.parse("data.csv", content)
    assert len(result) == 2
    assert result[0] == {"user_phone": "13800138001", "sms_code": "123456"}
    assert result[1] == {"user_phone": "13900139002", "sms_code": "654321"}


def test_parse_csv_utf8_bom(parser):
    """CSV with UTF-8 BOM should be parsed correctly."""
    # Encode with utf-8-sig adds the BOM prefix automatically
    content = "name,value\nfoo,bar\n".encode("utf-8-sig")
    result = parser.parse("data.csv", content)
    assert result == [{"name": "foo", "value": "bar"}]


def test_parse_csv_empty_cell(parser):
    """Empty cells become empty strings, not errors."""
    content = _make_csv([
        ["a", "b"],
        ["1", ""],
    ])
    result = parser.parse("data.csv", content)
    assert result == [{"a": "1", "b": ""}]


def test_parse_csv_skips_blank_rows(parser):
    """Completely blank rows are skipped."""
    content = _make_csv([
        ["a", "b"],
        ["1", "2"],
        ["", ""],
        ["3", "4"],
    ])
    result = parser.parse("data.csv", content)
    assert len(result) == 2


def test_parse_csv_no_data_rows(parser):
    content = _make_csv([["a", "b"]])
    with pytest.raises(ValueError, match="no data rows"):
        parser.parse("data.csv", content)


def test_parse_csv_empty_header(parser):
    content = b"\n1,2\n"
    with pytest.raises(ValueError):
        parser.parse("data.csv", content)


def test_parse_csv_invalid_utf8(parser):
    with pytest.raises(ValueError, match="UTF-8"):
        parser.parse("data.csv", b"\xff\xfe invalid")


# ── Excel parsing ─────────────────────────────────────────────────────────────

def _make_xlsx(rows: list[list]) -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    for row in rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_parse_excel_basic(parser):
    content = _make_xlsx([
        ["user_phone", "sms_code"],
        ["13800138001", "123456"],
        ["13900139002", "654321"],
    ])
    result = parser.parse("data.xlsx", content)
    assert len(result) == 2
    assert result[0] == {"user_phone": "13800138001", "sms_code": "123456"}


def test_parse_excel_empty_cell(parser):
    content = _make_xlsx([
        ["a", "b"],
        ["1", None],
    ])
    result = parser.parse("data.xlsx", content)
    assert result == [{"a": "1", "b": ""}]


def test_parse_excel_skips_blank_rows(parser):
    content = _make_xlsx([
        ["a", "b"],
        ["1", "2"],
        [None, None],
        ["3", "4"],
    ])
    result = parser.parse("data.xlsx", content)
    assert len(result) == 2


def test_parse_excel_no_data_rows(parser):
    content = _make_xlsx([["a", "b"]])
    with pytest.raises(ValueError, match="no data rows"):
        parser.parse("data.xlsx", content)


def test_parse_excel_empty_file(parser):
    wb = openpyxl.Workbook()
    ws = wb.active
    # Leave sheet empty
    buf = io.BytesIO()
    wb.save(buf)
    with pytest.raises(ValueError, match="empty"):
        parser.parse("data.xlsx", buf.getvalue())


def test_parse_excel_xls_extension_accepted(parser):
    """xls extension routes to Excel parser (openpyxl can read xlsx bytes)."""
    content = _make_xlsx([["k"], ["v"]])
    result = parser.parse("data.xls", content)
    assert result == [{"k": "v"}]


# ── File size limit ───────────────────────────────────────────────────────────

def test_parse_rejects_oversized_file(parser):
    oversized = b"a" * (2 * 1024 * 1024 + 1)
    with pytest.raises(ValueError, match="2 MB"):
        parser.parse("data.csv", oversized)


# ── Unsupported type ──────────────────────────────────────────────────────────

def test_parse_unsupported_type(parser):
    with pytest.raises(ValueError, match="Unsupported"):
        parser.parse("data.txt", b"hello")


def test_parse_no_extension(parser):
    with pytest.raises(ValueError, match="Unsupported"):
        parser.parse("noext", b"hello")
