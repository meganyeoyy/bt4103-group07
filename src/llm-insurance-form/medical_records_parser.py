import json
import yaml
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import fitz
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

class MedicalRecordsParser:
    def __init__(self):
        with open("medical_records_parser_config.yaml", "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

    # =====================================================
    # 1. PDF TEXT CLEANING (headers/footers)
    # =====================================================
    def extract_text_no_header_footer(self, pdf_path: Union[str, Path]) -> str:
        """Extract PDF text while removing hospital headers and footers."""
        doc = fitz.open(pdf_path)
        pages = []

        hospital_patterns = "|".join(self.config["pdf_cleaning"]["hospital_patterns"])
        footer_patterns = self.config["pdf_cleaning"]["footer_patterns"]

        for page in doc:
            text = page.get_text("text").replace("#—! ", "")

            # Remove header (hospital + current location lines)
            text = re.sub(
                rf"(?m)^\s*(?:{hospital_patterns})\s*\n^\s*Current Location:.*(?:\n\s*\S.*)?",
                "",
                text,
            )

            # Remove footers
            for pattern in footer_patterns:
                text = re.sub(rf"(?im)^\s*{pattern}.*$", "", text)

            pages.append(text.strip())

        return "\n\n".join(pages)

    # =====================================================
    # 2. DMO SECTION DETECTION
    # =====================================================
    def match_dmo_section_header(self, line: str) -> Optional[re.Match]:
        pattern = re.compile(self.config["metadata"]["dmo_header_regex"], re.IGNORECASE)
        return pattern.match(line.strip())

    def is_dmo_section_header(self, line: str) -> bool:
        return bool(self.match_dmo_section_header(line))

    def is_ignored_section_header(self, line: str) -> bool:
        ignored = self.config["section_headers"]["ignored"]
        return any(line.strip().upper().startswith(h.upper()) for h in ignored)

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

    def extract_dmo_sections(self, text: str) -> List[str]:
        lines = text.splitlines()
        sections, current = [], []
        capturing = False

        for raw_line in lines:
            line = raw_line.rstrip("\n")
            if self.is_junk_line(line):
                continue
            if self.is_ignored_section_header(line):
                capturing = False
                current = []
                continue
            if self.is_dmo_section_header(line):
                if capturing and current:
                    sections.append("\n".join(current))
                capturing = True
                current = [line]
                continue
            if capturing:
                current.append(line)
                if self.is_last_updated_line(line):
                    sections.append("\n".join(current))
                    current = []
                    capturing = False
        if capturing and current:
            sections.append("\n".join(current))
        return sections

    # =====================================================
    # 3. SUBSECTION SPLITTING
    # =====================================================
    def split_into_subsections(self, text: str) -> Dict[str, str]:
        headers = self.config["section_headers"]["subsections"]
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

    # =====================================================
    # 4. METADATA PARSING
    # =====================================================
    def parse_dmo_metadata(self, section: str) -> Tuple[str, str, str]:
        authored_date_pattern = self.config["metadata"]["authored_date_pattern"]
        last_updated_pattern = self.config["metadata"]["last_updated_pattern"]

        authored_match = re.search(authored_date_pattern, section)
        authored_date = authored_match.group(1) if authored_match else "UNKNOWN"

        doctor_match = re.search(last_updated_pattern, section)
        doctor = doctor_match.group(1).strip() if doctor_match else "UNKNOWN"

        header_match = self.match_dmo_section_header(section.splitlines()[0])
        section_type = header_match.group(1) if header_match else "UNKNOWN"

        return authored_date, doctor, section_type

    # =====================================================
    # 5. TEXT CLEANING
    # =====================================================
    def month_abbr_to_num(self, abbr: str) -> str:
        return self.config["normalization"]["month_map"].get(abbr, "01")

    def normalize_formatting(self, text: str) -> str:
        abbr_map = self.config["normalization"]["abbreviation_map"]
        text = re.sub(
            r"(\d{1,2})-([A-Za-z]{3})-(\d{4})",
            lambda m: f"{m.group(3)}-{self.month_abbr_to_num(m.group(2))}-{int(m.group(1)):02d}",
            text,
        )
        for abbr, full in abbr_map.items():
            text = re.sub(rf"\b{abbr}\b", full, text)
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

    # =====================================================
    # 6. ENRICHMENT
    # =====================================================
    def extract_allergies(self, text: str) -> Optional[str]:
        if "No Known Allergies" in text or "nil known" in text.lower():
            return "NKA"
        if m := re.search(r"Allergies[: ]+(.*)", text):
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

    # =====================================================
    # 7. TIMELINE BUILDER
    # =====================================================
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
    # scannedPdfConverter(r"../../data/SCM Records/Redacted - SCM_Patient 3.pdf", r"../../data/SCM Records/Converted/Redacted - SCM_Patient 3_Converted.pdf")

    pdf_path = f"../../data/SCM Records/Converted/Redacted - SCM_Patient 3_Converted.pdf"
    parser = MedicalRecordsParser()
    timeline = parser.build_timeline(pdf_path)

    # print(json.dumps(timeline, indent=2))
    with open(
        f"../../data/SCM Records/Converted/Patient 3 Medical Records.json",
        "w",
        encoding="utf-8",
    ) as f:
        f.write(json.dumps(timeline, indent=2))
