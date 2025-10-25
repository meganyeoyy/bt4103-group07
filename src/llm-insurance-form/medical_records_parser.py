import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import fitz
import yaml


class MedicalRecordsParser:
    def __init__(
        self, config_path: Union[str, Path] = "medical_records_parser_config.yaml"
    ):
        # Load YAML config
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)

        self.cfg = cfg
        self.DMO_HEADER_REGEX = re.compile(
            r".{0,10}?"  # allow up to 10 junk chars before DMO
            r"DMO\s*"  # DMO keyword
            r"("  # Capture section type
            r"Consult|Correspondence|Pre[- ]?clerk\s*Consult|"
            r"Inpatient\s*(?:Admission\s*Note|Daily\s*Ward\s*Round(?:\s*V\d+)?)|"
            r"Correspondence\s*Note"
            r")"  # Capture Section type
            r".{0,50}?\[Charted\s*Location:",
            re.IGNORECASE | re.DOTALL,
        )

        # metadata patterns
        self._authored_date_re = re.compile(
            r"Authored:\s*(\d{1,2}-[A-Za-z]{3}-\d{4})", re.IGNORECASE
        )
        self._last_updated_re = re.compile(
            r"Last\s*Updated:.*?by\s+([A-Za-z\s\-]+)\s*\(Doctor\)",
        )

        # ---------- LOAD CONFIGURED PATTERNS / MAPS ----------
        pdf_clean = cfg.get("pdf_cleaning", {})
        self.hospital_patterns = [
            re.compile(p, re.IGNORECASE) for p in pdf_clean.get("hospital_patterns", [])
        ]
        self.footer_patterns = [
            re.compile(p, re.IGNORECASE) for p in pdf_clean.get("footer_patterns", [])
        ]

        section_cfg = cfg.get("section_headers", {})
        self.ignored_headers = section_cfg.get("ignored", [])
        self.subsection_headers = section_cfg.get("subsections", [])

        norm = cfg.get("normalization", {})
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
            # Remove known artifact (kept from your earlier code)
            text = text.replace("#—! ", "")

            # filter out hospital header and footer lines
            lines = []
            for line in text.splitlines():
                # skip hospital header lines
                if any(p.search(line) for p in self.hospital_patterns):
                    continue
                # skip footer lines
                if any(p.search(line) for p in self.footer_patterns):
                    continue
                lines.append(line)
            pages.append("\n".join(lines).strip())
        return "\n\n".join(pages)

    # -------------------------
    # HELPERS: header/junk detection
    # -------------------------
    def match_dmo_section_header(self, line: str) -> Optional[re.Match]:
        clean_line = re.sub(r"^[^\w]*", "", line)

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
        if re.fullmatch(r"([^\w\s])\1{8,}", text):
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
        pattern = "(" + "|".join([re.escape(h) + ":?" for h in headers]) + ")"

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
    # METADATA PARSING (HARD-CODED PATTERNS)
    # -------------------------
    def parse_dmo_metadata(self, section: str) -> Tuple[str, str, str]:
        authored_match = self._authored_date_re.search(section)
        authored_date = authored_match.group(1) if authored_match else "UNKNOWN"

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
        text = re.sub(
            r"(\d{1,2})-([A-Za-z]{3})-(\d{4})",
            lambda m: f"{m.group(3)}-{self.month_abbr_to_num(m.group(2))}-{int(m.group(1)):02d}",
            text,
        )
        for abbr, full in self.abbr_map.items():
            # word boundary replacement where reasonable
            text = re.sub(rf"\b{re.escape(abbr)}\b", full, text)
        text = text.replace("\n", " ")
        text = re.sub(r"[^\x00-\x7F]+", "", text)
        return text

    def remove_admin_noise(self, text: str) -> str:
        text = re.sub(r"(?im)^\s*Electronic Signatures:.*$", "", text)
        text = re.sub(r"(?im)^\s*Authored:.*$", "", text)
        text = re.sub(r"(?im)^\s*[A-Za-z\s\.\-]+\(Doctor\)\s*\(Signed.*$", "", text)
        text = re.sub(r"(?im)^\s*Last Updated:.*$", "", text)
        text = re.sub(r"(?m)^\s*\|\s*", "", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    # -------------------------
    # ENRICHMENT
    # -------------------------
    def extract_allergies(self, text: str) -> Optional[str]:
        if "No Known Allergies" in text or "nil known" in text.lower():
            return "NKA"
        m = re.search(r"Allergies[: ]+(.*)", text, re.IGNORECASE)
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


if __name__ == "__main__":
    # TODO: Changes to be made based on where the files are stored after user upload; part of integration work
    # Example usage as below:
    # scannedPdfConverter(r"../../data/SCM Records/Redacted - SCM_Patient 5.pdf", r"../../data/SCM Records/Converted/Redacted - SCM_Patient 5_Converted.pdf")

    pdf_path = (
        f"../../data/SCM Records/Converted/Redacted - SCM_Patient 1_Converted.pdf"
    )
    parser = MedicalRecordsParser()
    timeline = parser.build_timeline(pdf_path)

    # print(json.dumps(timeline, indent=2))
    with open(
        f"../../data/SCM Records/Converted/Patient 1 Medical Records.json",
        "w",
        encoding="utf-8",
    ) as f:
        f.write(json.dumps(timeline, indent=2))
