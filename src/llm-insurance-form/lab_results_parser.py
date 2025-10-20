import fitz
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


class LabResultParser:
    """
    A class designed to process and parse laboratory report PDFs.

    It extracts cleaned text, and structures the lab test results into a 
    chronological timeline format.
    """

    def __init__(self, pdf_path: Union[str, Path]):
        """
        Initializes the parser with the path to the PDF file.

        Args:
            pdf_path (Union[str, Path]): Path to the PDF file.
        """
        self.pdf_path = Path(pdf_path)
        self._timeline: Dict[str, List[Dict[str, str]]] = {}

    def _extract_cleaned_text(self) -> str:
        """
        Extracts text from the PDF pages using PyMuPDF (fitz) while 
        removing repeating headers and footers based on defined patterns.

        Returns:
            str: The concatenated and cleaned text content of the PDF.
        """
        try:
            doc = fitz.open(self.pdf_path)
        except Exception as e:
            print(f"Error opening PDF: {e}")
            return ""
            
        cleaned_pages = []

        # Compile header/footer patterns for efficiency
        header_pattern = re.compile(
            r"^\s*(?:national cancer centre|singapore general hospital|.*hospital.*?)\s*" 
            r".*?"
            r"Requested By:.*?\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{1,2}\s*\n*", 
            re.DOTALL | re.IGNORECASE
        )
        footer_patterns = [
            re.compile(r"(?im)^\s*this is a computer generated report.*$", re.MULTILINE),
            re.compile(r"(?im)^\s*printed from:.*$", re.MULTILINE),
            re.compile(r"(?im)^\s*page:\s*\d+\s*$", re.MULTILINE),
            re.compile(r"(?im)^\s*requested by:.*page\s*\d+\s*of\s*\d+.*$", re.MULTILINE),
            re.compile(r"(?im)End of Report\s*$", re.MULTILINE)
        ]

        for page in doc:
            text = page.get_text("text")

            # 1. Remove Header
            text = header_pattern.sub("", text)

            # 2. Remove Footer lines
            for pat in footer_patterns:
                text = pat.sub("", text)

            # 3. Clean up generic noise
            text = re.sub(r"[^\x00-\x7F\n\r]+", "", text) # Remove non-ASCII/unicode noise
            text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text) # Collapse multiple blank lines
            text = re.sub(r" {2,}", " ", text) # Collapse multiple spaces

            cleaned_pages.append(text.strip())

        return "\n\n".join(cleaned_pages)

    @staticmethod
    def _clean_test_name(test_name_header: str) -> str:
        """
        Cleans and normalizes the raw text found immediately after the date/time stamp
        to derive a consistent test name for aggregation.
        """
        # 1. Aggressively stop name extraction before common delimiters, IDs, or boilerplates
        test_name = re.match(
            r"(.*?)(?:\s+(?:\d{4}:\w{4}|[A-Z]{2}:[A-Z]{2}\d+|\d{2}:\d+|\d{4}|\d{1,2}|Final|Report Link|Additional Info|Verified|Reporting|Received|HISTORY|DIAGNOSIS|\()|$)", 
            test_name_header, re.IGNORECASE
        )
        
        # Use the captured group 1 or fall back to the header if the pattern didn't match
        clean_name = test_name.group(1).strip() if test_name and test_name.group(1) else test_name_header

        # 2. Remove common, non-essential descriptor words that cause fragmentation
        clean_name = re.sub(r"\(this test is to be.*\)", "", clean_name).strip()
        clean_name = re.sub(r"(Screening Test|Profile|serum|POCT|Antibody|Report|Link|Additional Info|Verified|SGCR|Erect)", "", clean_name, flags=re.IGNORECASE).strip()
        
        # 3. Collapse multiple spaces and remove trailing punctuation/spaces
        clean_name = re.sub(r"\s+", " ", clean_name).strip()
        
        # Final fix for specific long names
        if "Anti Double-stranded DNA" in clean_name:
            clean_name = "Anti Double-stranded DNA Antibody" 
            
        return clean_name

    @staticmethod
    def _parse_all_tests(text: str) -> List[Dict[str, str]]:
        """
        Splits the raw text by the date-time stamp, cleans the test name, and aggregates
        consecutive blocks that belong to the same test (same date and same cleaned name).
        """
        # Pattern to capture the Date-Time stamp (the start of a new test block)
        split_pattern = re.compile(r"(\d{1,2}-[A-Za-z]{3}-\d{4}\s+\d{2}:\d{2})\s*", re.DOTALL)
        
        # Split the text by the Date-Time stamps, including the stamps in the result
        parts = split_pattern.split(text)
        
        initial_tests = []
        
        # 1. INITIAL SPLIT AND CLEANING
        for i in range(1, len(parts), 2):
            stamp = parts[i].strip() # e.g., "20-Jun-2025 00:16"
            body = parts[i+1].strip() if i+1 < len(parts) else ""
            
            date_match = re.match(r"(\d{1,2}-[A-Za-z]{3}-\d{4})", stamp)
            date = date_match.group(1).strip() if date_match else "Unknown Date"
            
            # Heuristically find the test name from the text *after* the stamp
            test_name_header = body.split('\n', 1)[0].strip()
            
            test_name = LabResultParser._clean_test_name(test_name_header)
            
            if test_name and body:
                initial_tests.append({
                    "date": date,
                    "test_name": test_name,
                    "raw_details": body
                })
                
        # 2. AGGREGATE CONSECUTIVE BLOCKS
        if not initial_tests:
            return []

        aggregated_tests = []
        current_test = initial_tests[0]
        
        # Helper to create a simplified key for comparison
        def get_comparison_key(date, test_name):
            # Normalizes the name for reliable comparison
            return date + "-" + re.sub(r'[,\s\.]', '', test_name).lower()

        for i in range(1, len(initial_tests)):
            next_test = initial_tests[i]
            
            current_key = get_comparison_key(current_test['date'], current_test['test_name'])
            next_key = get_comparison_key(next_test['date'], next_test['test_name'])
            
            # If the date and normalized test name are the same, merge the raw text
            if current_key == next_key:
                # Merge: Use a separator to clearly delineate where blocks merged
                current_test['raw_details'] += "\n\n\n" + next_test['raw_details']
            else:
                # The current test block is complete, move it to the aggregated list
                aggregated_tests.append(current_test)
                # Start a new block
                current_test = next_test

        # Append the very last test block
        if current_test:
            aggregated_tests.append(current_test)

        # Return the merged tests
        return aggregated_tests
        
    def parse(self) -> Dict[str, List[Dict[str, str]]]:
        """
        The main method to execute the full parsing workflow.

        1. Extracts and cleans raw text from the PDF.
        2. Parses the text into individual, aggregated test results.
        3. Structures the results into a final chronological dictionary format.

        Returns:
            Dict[str, List[Dict[str, str]]]: The structured lab timeline.
        """
        print(f"Starting parsing for PDF: {self.pdf_path.name}")
        raw_text = self._extract_cleaned_text()
        
        if not raw_text:
            print("Extraction failed or resulted in empty text.")
            return {}

        # 1. Parse and aggregate all tests into a flat list
        flat_tests = self._parse_all_tests(raw_text)
        
        # 2. Build the final JSON structure using a list of dictionaries per date
        timeline = defaultdict(list)

        for item in flat_tests:
            date = item['date']
            test_name = item['test_name']
            raw_details_text = item['raw_details']

            # Final clean-up of the test body text
            details_text = re.sub(r"(Final\s*Updated|Final|Updated|I\s*1|SGCR\d+|(?:\d{2}:\w{2}\d{4}))\s*", " ", raw_details_text, flags=re.IGNORECASE)
            details_text = re.sub(r"\s*\n\s*", "\n", details_text) # Collapse lines
            details_text = re.sub(r" {2,}", " ", details_text).strip() # Collapse spaces

            # Append the structured result to the timeline
            timeline[date].append({
                "test_name": test_name,
                "text": details_text
            })

        self._timeline = dict(timeline)
        print(f"Parsing complete. Found {len(self._timeline)} unique dates with results.")
        return self._timeline

# --------------------------------------------------
# For testing purposes
# --------------------------------------------------
if __name__ == "__main__":
    scannedPdfConverter(r"../../data/Lab Results/Redacted - Lab Results_Patient4.pdf", r"../../data/Lab Results/Converted/Redacted - Lab Results_Patient4_Converted.pdf")
    pdf_path = r"../../data/Lab Results/Converted/Redacted - Lab Results_Patient4_Converted.pdf"
    parser = LabResultParser(pdf_path)
    timeline = parser.parse()

    # print(json.dumps(timeline, indent=2))
    with open(r"../../data/Lab Results/Converted/Patient 4 Lab Results.json", "w", encoding="utf-8") as f:
        f.write(json.dumps(timeline, indent=2))
