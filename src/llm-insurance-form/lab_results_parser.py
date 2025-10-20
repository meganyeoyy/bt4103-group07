import fitz
import yaml
import re
import json
from collections import defaultdict
from typing import Dict, List, Optional, Tuple, Union
from pathlib import Path

import ocrmypdf


def scannedPdfConverter(
    file_path: Union[str, Path], save_path: Union[str, Path]
) -> None:
    """
    Convert a scanned PDF into a searchable/selectable PDF using OCR.

    Args:
        file_path (Union[str, Path]): Path to the scanned PDF file.
        save_path (Union[str, Path]): Path where the converted PDF should be saved.

    Returns:
        None
    """
    ocrmypdf.ocr(file_path, save_path, skip_text=True)
    print("File converted successfully!")


################################################
class LabResultParser:
    def __init__(self):
        """Initialize parser and load YAML config."""
        with open("lab_results_parser_config.yaml", "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

    # =====================================================
    # 1. PDF TEXT CLEANING
    # =====================================================
    def extract_text_no_header_footer(self, pdf_path: Union[str, Path]) -> str:
        """Extract PDF text while removing headers and footers."""
        doc = fitz.open(pdf_path)
        pages = []

        header_patterns = [
            re.compile(pat, re.IGNORECASE | re.MULTILINE)
            for pat in self.config["pdf_cleaning"]["header_patterns"]
        ]
        footer_patterns = [
            re.compile(pat, re.IGNORECASE | re.MULTILINE)
            for pat in self.config["pdf_cleaning"]["footer_patterns"]
        ]

        for page in doc:
            text = page.get_text("text")

            # Remove headers
            for pat in header_patterns:
                text = pat.sub("", text)

            # Remove footers
            for pat in footer_patterns:
                text = pat.sub("", text)

            # Cleanup text
            if self.config["text_cleanup"]["remove_non_ascii"]:
                text = re.sub(r"[^\x00-\x7F\n\r]+", "", text)
            if self.config["text_cleanup"]["collapse_blank_lines"]:
                text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
            if self.config["text_cleanup"]["collapse_spaces"]:
                text = re.sub(r" {2,}", " ", text)

            pages.append(text.strip())

        return "\n\n".join(pages)

    # =====================================================
    # 2. TEST NAME CLEANING
    # =====================================================
    def clean_test_name(self, raw_header: str) -> str:
        """Normalize and clean test names."""
        stopwords = "|".join(self.config["test_detection"]["name_stopwords"])
        match = re.match(rf"(.*?)(?:\s+(?:{stopwords})|$)", raw_header, re.IGNORECASE)

        clean_name = match.group(1).strip() if match and match.group(1) else raw_header
        clean_name = re.sub(r"\s+", " ", clean_name).strip()

        return clean_name

    # =====================================================
    # 3. PARSE ALL TESTS
    # =====================================================
    def parse_all_tests(self, text: str) -> List[Dict[str, str]]:
        """Split and group all lab test sections by date."""
        datetime_pattern = re.compile(
            self.config["test_detection"]["datetime_pattern"], re.DOTALL
        )
        date_pattern = re.compile(self.config["test_detection"]["date_pattern"])

        parts = datetime_pattern.split(text)
        tests = []

        for i in range(1, len(parts), 2):
            stamp = parts[i].strip()
            body = parts[i + 1].strip() if i + 1 < len(parts) else ""
            date_match = date_pattern.match(stamp)
            date = date_match.group(1) if date_match else "UNKNOWN"

            test_header = body.split("\n", 1)[0].strip()
            test_name = self.clean_test_name(test_header)

            if test_name and body:
                tests.append(
                    {"date": date, "test_name": test_name, "raw_details": body}
                )

        # Aggregate consecutive blocks with same date/test name
        aggregated = []
        current = tests[0] if tests else None

        def key(d, n):
            return d + "-" + re.sub(r"[,\s\.]", "", n).lower()

        for next_test in tests[1:]:
            if key(current["date"], current["test_name"]) == key(
                next_test["date"], next_test["test_name"]
            ):
                current["raw_details"] += "\n\n" + next_test["raw_details"]
            else:
                aggregated.append(current)
                current = next_test
        if current:
            aggregated.append(current)

        return aggregated

    # =====================================================
    # 4. TEXT NORMALIZATION
    # =====================================================
    def normalize_test_details(self, text: str) -> str:
        """Clean up test detail text."""
        cleanup_words = "|".join(self.config["cleanup_words"])
        text = re.sub(rf"({cleanup_words})\s*", " ", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*\n\s*", "\n", text)
        text = re.sub(r" {2,}", " ", text).strip()
        return text

    # =====================================================
    # 5. TIMELINE BUILDER
    # =====================================================
    def build_timeline(self, pdf_path: Union[str, Path]) -> Dict[str, List[Dict]]:
        """Build chronological test results timeline."""
        raw_text = self.extract_text_no_header_footer(pdf_path)
        tests = self.parse_all_tests(raw_text)

        timeline = defaultdict(list)
        for test in tests:
            cleaned = self.normalize_test_details(test["raw_details"])
            timeline[test["date"]].append(
                {"test_name": test["test_name"], "text": cleaned}
            )

        return dict(timeline)


if __name__ == "__main__":
    pdf_path = (
        "../../data/Lab Results/Converted/Redacted - Lab Results_Patient4_Converted.pdf"
    )
    parser = LabResultParser()
    timeline = parser.build_timeline(pdf_path)

    with open(
        "../../data/Lab Results/Converted/Patient 4 Lab Results.json",
        "w",
        encoding="utf-8",
    ) as f:
        f.write(json.dumps(timeline, indent=2))
