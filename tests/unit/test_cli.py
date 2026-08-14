import os
import pytest
from pii_redactor.cli import parse_args, main
from docx import Document

def create_simple_test_docx(file_path: str):
    doc = Document()
    doc.add_paragraph("This is test file for CLI. Contact: user@test.com.")
    doc.save(file_path)

def test_cli_parser():
    """
    Checks that arguments are parsed correctly.
    """
    args = ["--input", "in.docx", "--output", "out.docx", "--seed", "42", "--confidence-threshold", "0.85", "--verbose"]
    parsed = parse_args(args)
    assert parsed.input == "in.docx"
    assert parsed.output == "out.docx"
    assert parsed.seed == 42
    assert parsed.confidence_threshold == 0.85
    assert parsed.verbose is True

def test_cli_parser_missing_required():
    """
    Checks that parser exits when required arguments are missing.
    """
    with pytest.raises(SystemExit):
        parse_args(["--input", "in.docx"])  # Missing --output

def test_cli_main_success(tmp_path):
    """
    Verifies that running CLI main executes and returns 0 exit code.
    """
    input_path = os.path.join(tmp_path, "in.docx")
    output_path = os.path.join(tmp_path, "out.docx")
    create_simple_test_docx(input_path)

    # Run cli.main programmatically
    args = ["-i", input_path, "-o", output_path, "-s", "123", "-c", "0.80"]
    exit_code = main(args)
    
    assert exit_code == 0
    assert os.path.exists(output_path)
