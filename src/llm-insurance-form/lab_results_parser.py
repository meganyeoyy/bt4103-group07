import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Union

import fitz
import yaml


class LabResultParser:
    def __init__(self):
        """Initialize parser and load YAML config."""
        with open("lab_results_parser_config.yaml", "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

    # =====================================================
    # 1. PDF TEXT CLEANING
    # =====================================================
    def extract_text_no_header_footer(self, pdf_path: Union[str, Path]) -> str:
        """
        Extract PDF text while removing headers and footers.

        Params:
            pdf_path (Union[str, Path]): Path to the lab results PDF file.
        Returns:
            str: Cleaned text extracted from the PDF.
        """
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
        """
        Normalize and clean test names extracted from lab results.

        Params:
            raw_header (str): Raw test name/header extracted from the PDF.

        Returns:
            str: Cleaned test name.
        """
        stopwords = "|".join(self.config["test_detection"]["name_stopwords"])
        match = re.match(rf"(.*?)(?:\s+(?:{stopwords})|$)", raw_header, re.IGNORECASE)

        clean_name = match.group(1).strip() if match and match.group(1) else raw_header
        clean_name = re.sub(r"\s+", " ", clean_name).strip()

        return clean_name

    # =====================================================
    # 3. PARSE ALL TESTS
    # =====================================================
    def parse_all_tests(self, text: str) -> List[Dict[str, str]]:
        """
        Split and group all lab test sections by date.

        Params:
            text (str): Full raw text extracted from the lab results PDF.
        Returns:
            List[Dict[str, str]]: List of dictionaries with keys: date, test_name, raw_details.
        """
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
        """
        Clean up test detail text.

        Params:
            text (str): Raw test detail text.

        Returns:
            str: Cleaned test detail text.
        """
        cleanup_words = "|".join(self.config["cleanup_words"])
        text = re.sub(rf"({cleanup_words})\s*", " ", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*\n\s*", "\n", text)
        text = re.sub(r" {2,}", " ", text).strip()
        return text

    # =====================================================
    # 5. TIMELINE BUILDER
    # =====================================================
    def build_timeline(self, pdf_path: Union[str, Path]) -> Dict[str, List[Dict]]:
        """
        Build chronological test results timeline with the requested nested structure:
        Date -> [ { "lab results": { Test Name: Text, ... } } ]

        Params:
            pdf_path (Union[str, Path]): Path to the lab results PDF file.

        Returns:
            Dict[str, List[Dict]]: Timeline dictionary.
        """
        raw_text = self.extract_text_no_header_footer(pdf_path)
        tests = self.parse_all_tests(raw_text)

        # 1. Group all individual tests into a temporary dictionary by date.
        # The value for each date will be a dictionary of {test_name: details}.
        tests_by_date = defaultdict(dict)

        for test in tests:
            cleaned = self.normalize_test_details(test["raw_details"])
            # The inner dictionary structure: {test_name: cleaned_text}
            tests_by_date[test["date"]][test["test_name"]] = cleaned

        # 2. Build the final timeline structure: Date -> [ { "lab results": { ... } } ]
        final_timeline = {}
        for date, results_dict in tests_by_date.items():
            final_timeline[date] = [{"lab results": results_dict}]

        return final_timeline


if __name__ == "__main__":
    # Example usage
    pdf_path = (
        "../../data/Lab Results/Converted/Redacted - Lab Results_Patient2_Converted.pdf"
    )
    parser = LabResultParser()
    timeline = parser.build_timeline(pdf_path)

    with open(
        "../../data/Lab Results/Converted/Patient 2 Lab Results.json",
        "w",
        encoding="utf-8",
    ) as f:
        f.write(json.dumps(timeline, indent=2))
