import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import fitz
import yaml


class MedicalRecordsParser:
    # --- REGEX PATTERNS (Centralized) ---

    # REGEX: Matches the main DMO section header (e.g., "DMO Consult Note").
    # It captures the section type (e.g., "Consult", "Inpatient Admission Note").
    _REGEX_DMO_HEADER = (
        r".{0,10}?"  # Allow up to 10 junk chars before DMO
        r"DMO\s*"  # DMO keyword
        r"("  # Start capture Section Type
        r"Consult|Correspondence|Pre[- ]?clerk\s*Consult|"
        r"Inpatient\s*(?:Admission\s*Note|Daily\s*Ward\s*Round(?:\s*V\d+)?)|"
        r"Correspondence\s*Note"
        r")"  # End capture Section Type
        r".{0,50}?\[Charted\s*Location:"  # Lookahead to confirm it's a header pattern
    )

    # REGEX: Extracts the date from an "Authored:" line. Captures the date.
    _REGEX_AUTHORED_DATE = r"Authored:\s*(\d{1,2}-[A-Za-z]{3}-\d{4})"

    # REGEX: Extracts the doctor's name from a "Last Updated:" line. Captures the name.
    _REGEX_LAST_UPDATED_DOCTOR = r"Last\s*Updated:.*?by\s+([A-Za-z\s\-]+)\s*\(Doctor\)"

    # REGEX: Identifies lines that are likely junk/artifacts (e.g., '------' or '*******').
    _REGEX_JUNK_LINE = r"([^\w\s])\1{8,}"

    # REGEX: Normalizes DD-MMM-YYYY date formats into YYYY-MM-DD.
    _REGEX_DATE_NORMALIZE = r"(\d{1,2})-([A-Za-z]{3})-(\d{4})"

    # REGEX: Removes non-ASCII characters.
    _REGEX_NON_ASCII = r"[^\x00-\x7F]+"

    # REGEX: Matches and removes various administrative noise lines from the body.
    _REGEX_ADMIN_NOISE = [
        r"^\s*Electronic Signatures:.*$",
        r"^\s*Authored:.*$",
        r"^\s*[A-Za-z\s\.\-]+\(Doctor\)\s*\(Signed.*$",
        r"^\s*Last Updated:.*$",
        r"^\s*\|\s*",  # Matches vertical bar artifacts at the start of a line
    ]

    # REGEX: Collapses multiple blank lines.
    _REGEX_COLLAPSE_BLANK_LINES = r"\n{3,}"

    # REGEX: Extracts allergy information. Captures the details after "Allergies:".
    _REGEX_ALLERGIES = r"Allergies[: ]+(.*)"

    # -----------------------------------------------------------

    def __init__(self, config_path: Union[str, Path] = "document_parser_config.yaml"):
        """Initialize parser, load YAML config, and pre-compile regex patterns."""
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f).get("medical_records_config", {})

        # --- Pre-compile regex patterns ---
        self.DMO_HEADER_REGEX = re.compile(
            self._REGEX_DMO_HEADER, re.IGNORECASE | re.DOTALL
        )
        self._authored_date_re = re.compile(self._REGEX_AUTHORED_DATE, re.IGNORECASE)
        self._last_updated_re = re.compile(
            self._REGEX_LAST_UPDATED_DOCTOR, re.IGNORECASE
        )
        self._junk_line_re = re.compile(self._REGEX_JUNK_LINE)
        self._date_normalize_re = re.compile(self._REGEX_DATE_NORMALIZE)
        self._non_ascii_re = re.compile(self._REGEX_NON_ASCII)
        self._collapse_blank_lines_re = re.compile(self._REGEX_COLLAPSE_BLANK_LINES)
        self._allergies_re = re.compile(self._REGEX_ALLERGIES, re.IGNORECASE)

        # Compile admin noise patterns (use MULTILINE flag)
        self._admin_noise_patterns = [
            re.compile(pat, re.IGNORECASE | re.MULTILINE)
            for pat in self._REGEX_ADMIN_NOISE
        ]

        # --- Load non-regex patterns from config ---
        pdf_clean = self.config.get("pdf_cleaning", {})
        # These are simple string patterns, not regex
        self.hospital_patterns = pdf_clean.get("hospital_patterns", [])
        self.footer_patterns = pdf_clean.get("footer_patterns", [])

        section_config = self.config.get("section_headers", {})
        self.ignored_headers = section_config.get("ignored", [])
        self.subsection_headers = section_config.get("subsections", [])

        norm = self.config.get("normalization", {})
        self.month_map = norm.get("month_map", {})
        self.abbr_map = norm.get("abbreviation_map", {})

    # -------------------------
    # PDF TEXT EXTRACTION / CLEANING
    # -------------------------
    def extract_text_no_header_footer(self, pdf_path: Union[str, Path]) -> str:
        doc = fitz.open(pdf_path)
        pages: List[str] = []

        for page in doc:
            text = page.get_text("text")
            text = text.replace("#—! ", "")

            # filter out hospital header and footer lines (using simple string contains)
            lines = []
            for line in text.splitlines():
                line_lower = line.lower()
                # skip hospital header lines
                if any(p.lower() in line_lower for p in self.hospital_patterns):
                    continue
                # skip footer lines
                if any(p.lower() in line_lower for p in self.footer_patterns):
                    continue
                lines.append(line)
            pages.append("\n".join(lines).strip())
        return "\n\n".join(pages)

    # -------------------------
    # HELPERS: header/junk detection
    # -------------------------
    def match_dmo_section_header(self, line: str) -> Optional[re.Match]:
        # REGEX: Removes leading non-word characters before matching header
        clean_line = re.sub(r"^[^\w]*", "", line)

        # REGEX: Uses pre-compiled DMO header pattern
        match = self.DMO_HEADER_REGEX.search(clean_line)
        if match:
            return match
        return None

    def is_dmo_section_header(self, line: str) -> bool:
        return bool(self.match_dmo_section_header(line))

    def is_last_updated_line(self, line: str) -> bool:
        return line.strip().upper().startswith("LAST UPDATED:")

    def is_junk_line(self, line: str) -> bool:
        text = line.strip()
        if len(text) < 10:
            return False
        alnum = sum(1 for c in text if c.isalnum())
        ratio = alnum / max(1, len(text))
        if ratio < 0.25 or (len(text) > 30 and " " not in text and ratio < 0.5):
            return True
        # REGEX: Uses pre-compiled junk line pattern (e.g., '----')
        if self._junk_line_re.fullmatch(text):
            return True
        return False

    # -------------------------
    # SECTION EXTRACTION
    # -------------------------
    def extract_dmo_sections(self, text: str) -> list[str]:
        """
        Extracts all DMO sections from OCR text, ensuring each section includes
        the 'Last Updated ... (Doctor)' line at the end.
        """
        lines = text.splitlines()
        sections = []
        current = []
        inside_dmo = False

        for line in lines:
            line_stripped = line.strip()

            # Skip obvious junk lines
            if self.is_junk_line(line_stripped):
                continue

            # Detect start of DMO section
            if self.is_dmo_section_header(line):
                inside_dmo = True
                # Save previous section if exists
                if current:
                    sections.append("\n".join(current).strip())
                    current = []
                current.append(line_stripped)
                continue

            # If inside a DMO section, keep collecting lines
            if inside_dmo:
                current.append(line_stripped)
                # Check for Last Updated line that ends the section
                if self.is_last_updated_line(line_stripped):
                    inside_dmo = False
                    sections.append("\n".join(current).strip())
                    current = []

        if current:
            sections.append("\n".join(current).strip())

        return sections

    # -------------------------
    # SUBSECTION SPLITTING
    # -------------------------
    def split_into_subsections(self, text: str) -> Dict[str, str]:
        headers = self.subsection_headers
        normalized_headers = {h.upper(): h for h in headers}

        # REGEX: Dynamically builds a split pattern from config headers
        # e.g., (Header 1:?|Header 2:?)
        pattern = "(" + "|".join([re.escape(h) + ":?" for h in headers]) + ")"

        # REGEX: Splits the text by the dynamic header pattern
        parts = re.split(pattern, text, flags=re.IGNORECASE)
        subsections, buffer = {}, []
        current_header = "General"

        for part in parts:
            candidate = part.strip().rstrip(":")
            if candidate.upper() in normalized_headers:
                if buffer:
                    content = " ".join(buffer).strip()
                    if content:
                        subsections[current_header] = content
                    buffer = []
                current_header = normalized_headers[candidate.upper()]
            else:
                buffer.append(part)

        if buffer:
            content = " ".join(buffer).strip()
            if content:
                subsections[current_header] = content

        return {k: v for k, v in subsections.items() if v.strip()}

    # -------------------------
    # METADATA PARSING
    # -------------------------
    def parse_dmo_metadata(self, section: str) -> Tuple[str, str, str]:
        # REGEX: Uses pre-compiled pattern to find authored date
        authored_match = self._authored_date_re.search(section)
        authored_date = authored_match.group(1) if authored_match else "UNKNOWN"

        # REGEX: Uses pre-compiled pattern to find doctor's name
        doctor_match = self._last_updated_re.search(section)
        doctor = doctor_match.group(1).strip() if doctor_match else "UNKNOWN"

        header_match = self.match_dmo_section_header(section.splitlines()[0])
        section_type = header_match.group(1) if header_match else "UNKNOWN"

        return authored_date, doctor, section_type

    # -------------------------
    # CLEANING / NORMALIZATION
    # -------------------------
    def month_abbr_to_num(self, abbr: str) -> str:
        return self.month_map.get(abbr, "01")

    def normalize_formatting(self, text: str) -> str:
        # REGEX: Uses pre-compiled pattern to find and reformat dates
        text = self._date_normalize_re.sub(
            lambda m: f"{m.group(3)}-{self.month_abbr_to_num(m.group(2))}-{int(m.group(1)):02d}",
            text,
        )
        for abbr, full in self.abbr_map.items():
            # REGEX: Dynamically builds regex to replace abbreviations (e.g., '\bSOB\b')
            text = re.sub(rf"\b{re.escape(abbr)}\b", full, text)

        text = text.replace("\n", " ")
        # REGEX: Uses pre-compiled pattern to remove non-ASCII chars
        text = self._non_ascii_re.sub("", text)
        return text

    def remove_admin_noise(self, text: str) -> str:
        # REGEX: Uses pre-compiled list of admin noise patterns
        for pat in self._admin_noise_patterns:
            text = pat.sub("", text)

        # REGEX: Uses pre-compiled pattern to collapse blank lines
        text = self._collapse_blank_lines_re.sub("\n\n", text)
        return text.strip()

    # -------------------------
    # ENRICHMENT
    # -------------------------
    def extract_allergies(self, text: str) -> Optional[str]:
        if "No Known Allergies" in text or "nil known" in text.lower():
            return "NKA"
        # REGEX: Uses pre-compiled pattern to extract allergy details
        m = self._allergies_re.search(text)
        if m:
            return m.group(1).strip()
        return None

    def enrich_dmo_entry(self, section_dict: Dict[str, Union[str, Dict]]) -> Dict:
        subsections = self.split_into_subsections(section_dict["text"])
        enriched = {
            **section_dict,
            "subsections": list(subsections.keys()),
            "allergies": self.extract_allergies(section_dict["text"]),
            "text": subsections,
        }
        return enriched

    # -------------------------
    # TIMELINE BUILDER
    # -------------------------
    def build_timeline(self, pdf_path: Union[str, Path]) -> Dict[str, List[Dict]]:
        raw_text = self.extract_text_no_header_footer(pdf_path)
        dmo_sections = self.extract_dmo_sections(raw_text)

        timeline = defaultdict(list)
        for sec in dmo_sections:
            date, doctor, section_type = self.parse_dmo_metadata(sec)
            sec_clean = self.remove_admin_noise(sec)
            sec_clean = self.normalize_formatting(sec_clean)

            entry = {"doctor": doctor, "section_type": section_type, "text": sec_clean}
            enriched = self.enrich_dmo_entry(entry)
            timeline[date].append(enriched)

        return dict(timeline)


class LabResultParser:
    # --- REGEX PATTERNS (Centralized) ---

    # REGEX: General header patterns for removal. Uses MULTILINE/IGNORECASE flags.
    # We match line by line to avoid greedy consumption.
    _REGEX_HEADER_PATTERNS = [
        # REGEX: Matches 'National Cancer Centre', 'Patient Results', etc. at the start of a line.
        r"^\s*(?:National Cancer Centre|Patient Results|Singapore General Hospital|.*Hospital.*)\s*$",
        # REGEX: Matches 'All results performed dates from...' at the start of a line.
        r"^\s*All results performed dates from.*$",
        # REGEX: Matches 'Requested By: ... [date] [time]' at the start of a line.
        r"^\s*Requested By:.*?\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}\s*$",
        # REGEX: Matches 'Current Location:' line, which is often a header element.
        r"^\s*Current Location:.*$",
    ]

    # REGEX: General footer patterns for removal.
    _REGEX_FOOTER_PATTERNS = [
        # REGEX: Matches administrative footers related to report generation.
        r"^\s*this is a computer generated report.*$",
        # REGEX: Matches lines indicating where the document was printed from.
        r"^\s*printed from:.*$",
        # REGEX: Matches page numbers in common formats (e.g., 'Page: 1').
        r"^\s*page:\s*\d+\s*$",
        # REGEX: Matches page number variants often embedded in footer text.
        r"^\s*requested by:.*page\s*\d+\s*of\s*\d+.*$",
        # REGEX: Matches the final "End of Report" marker.
        r"End of Report\s*$",
    ]

    # REGEX: Pattern to split text blocks by date and time (e.g., 20-Jun-2025 00:16). Captures the timestamp.
    _REGEX_DATETIME_PATTERN = r"(\d{1,2}-[A-Za-z]{3}-\d{4}\s+\d{2}:\d{2})\s*"

    # REGEX: Pattern to extract just the date part (e.g., 20-Jun-2025). Captures the date.
    _REGEX_DATE_PATTERN = r"(\d{1,2}-[A-Za-z]{3}-\d{4})"

    # -----------------------------------------------------------

    def __init__(self, config_path: Union[str, Path] = "document_parser_config.yaml"):
        """Initialize parser and load YAML config."""
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f).get("lab_results_config", {})

        # Pre-compile the header and footer patterns now that they are internal
        self._compiled_header_patterns = [
            # REGEX: Compiling header patterns.
            # CRITICAL FIX: Use re.MULTILINE, not re.DOTALL.
            # re.MULTILINE makes ^ match the start of each line.
            # re.IGNORECASE makes the match case-insensitive.
            re.compile(pat, re.IGNORECASE | re.MULTILINE)
            for pat in self._REGEX_HEADER_PATTERNS
        ]
        self._compiled_footer_patterns = [
            # REGEX: Compiling footer patterns.
            # re.MULTILINE makes ^ and $ match start/end of lines.
            re.compile(pat, re.IGNORECASE | re.MULTILINE)
            for pat in self._REGEX_FOOTER_PATTERNS
        ]

    # =====================================================
    # 1. PDF TEXT CLEANING
    # =====================================================
    def extract_text_no_header_footer(self, pdf_path: Union[str, Path]) -> str:
        """
        Extract PDF text while removing headers and footers.
        """
        doc = fitz.open(pdf_path)
        pages = []

        # Header and footer patterns are already compiled in __init__
        header_patterns = self._compiled_header_patterns
        footer_patterns = self._compiled_footer_patterns

        for page in doc:
            text = page.get_text("text")

            # Remove headers
            for pat in header_patterns:
                text = pat.sub("", text)

            # Remove footers
            for pat in footer_patterns:
                text = pat.sub("", text)

            # Cleanup text
            # REGEX: Removes non-standard ASCII characters
            text = re.sub(r"[^\x00-\x7F\n\r]+", "", text)
            # REGEX: Collapses three or more consecutive newline/whitespace blocks into two newlines
            text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
            # REGEX: Collapses two or more consecutive spaces into a single space
            text = re.sub(r" {2,}", " ", text)

            pages.append(text.strip())

        return "\n\n".join(pages)

    # =====================================================
    # 2. TEST NAME CLEANING
    # =====================================================
    def clean_test_name(self, raw_header: str) -> str:
        """
        Normalize and clean test names extracted from lab results.
        """
        stopwords = "|".join(self.config["test_detection"]["name_stopwords"])
        # REGEX: Match and capture the test name (group 1), stopping before any defined stopword
        match = re.match(rf"(.*?)(?:\s+(?:{stopwords})|$)", raw_header, re.IGNORECASE)

        clean_name = match.group(1).strip() if match and match.group(1) else raw_header
        # REGEX: Collapse multiple spaces after stopword removal
        clean_name = re.sub(r"\s+", " ", clean_name).strip()

        return clean_name

    # =====================================================
    # 3. PARSE ALL TESTS
    # =====================================================
    def parse_all_tests(self, text: str) -> List[Dict[str, str]]:
        """
        Split and group all lab test sections by date.
        """
        # REGEX: Pattern to split text blocks by date and time (from internal constant)
        datetime_pattern = re.compile(self._REGEX_DATETIME_PATTERN, re.DOTALL)
        # REGEX: Pattern to extract just the date part (from internal constant)
        date_pattern = re.compile(self._REGEX_DATE_PATTERN)

        # REGEX: Split the entire document text, capturing the datetime stamp as a delimiter
        parts = datetime_pattern.split(text)
        tests = []

        for i in range(1, len(parts), 2):
            stamp = parts[i].strip()
            body = parts[i + 1].strip() if i + 1 < len(parts) else ""
            # REGEX: Matches and captures the date (group 1) from the timestamp string
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
            # REGEX: Normalizes test name by removing commas, spaces, and periods for stable comparison
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
        """
        cleanup_words = "|".join(self.config["cleanup_words"])
        # REGEX: Substitute all cleanup words (defined in YAML) with a single space
        text = re.sub(rf"({cleanup_words})\s*", " ", text, flags=re.IGNORECASE)
        # REGEX: Collapse empty lines/lines with only whitespace
        text = re.sub(r"\s*\n\s*", "\n", text)
        # REGEX: Collapse multiple spaces
        text = re.sub(r" {2,}", " ", text).strip()
        return text

    # =====================================================
    # 5. TIMELINE BUILDER
    # =====================================================
    def build_timeline(self, pdf_path: Union[str, Path]) -> Dict[str, List[Dict]]:
        """
        Build chronological test results timeline.
        """
        raw_text = self.extract_text_no_header_footer(pdf_path)
        tests = self.parse_all_tests(raw_text)

        # 1. Group all individual tests into a temporary dictionary by date.
        tests_by_date = defaultdict(dict)

        for test in tests:
            cleaned = self.normalize_test_details(test["raw_details"])
            tests_by_date[test["date"]][test["test_name"]] = cleaned

        # 2. Build the final timeline structure: Date -> [ { "lab results": { ... } } ]
        final_timeline = {}
        for date, results_dict in tests_by_date.items():
            final_timeline[date] = [{"lab results": results_dict}]

        return final_timeline


if __name__ == "__main__":
    # Example usage of MedicalRecordsParser
    medical_records_pdf_path = (
        f"../../../data/SCM Records/Converted/Redacted - SCM_Patient 1_Converted.pdf"
    )
    parser = MedicalRecordsParser()
    timeline = parser.build_timeline(medical_records_pdf_path)

    with open(
        f"../../../data/SCM Records/Converted/Patient 1 Medical Records.json",
        "w",
        encoding="utf-8",
    ) as f:
        f.write(json.dumps(timeline, indent=2))

    # Example usage of LabResultParser
    lab_results_pdf_path = f"../../../data/Lab Results/Converted/Redacted - Lab Results_Patient 1_Converted.pdf"
    parser = LabResultParser()
    timeline = parser.build_timeline(lab_results_pdf_path)

    with open(
        f"../../../data/Lab Results/Converted/Patient 1 Lab Results.json",
        "w",
        encoding="utf-8",
    ) as f:
        f.write(json.dumps(timeline, indent=2))
