import json
import re
import shutil
import time
from collections import defaultdict
from multiprocessing import Pool, cpu_count
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import fitz
import ocrmypdf

from lab_results_parser import LabResultParser
from medical_records_parser import MedicalRecordsParser

# --- Multiprocessing Worker Function (Global Scope) ---
def _is_pdf_searchable(file_path: Union[str, Path]) -> bool:
    """Helper to check if a PDF has a text layer."""
    try:
        doc = fitz.open(file_path)
        # Join text from all pages and strip whitespace
        text = "".join(page.get_text("text") for page in doc).strip()
        doc.close()
        return len(text) > 100
    except Exception as e:
        print(f"Error checking searchability for {Path(file_path).name}: {e}")
        return False


def _convert_scanned_pdf(
    file_path: Union[str, Path], save_path: Union[str, Path]
) -> None:
    """Convert a scanned PDF into a searchable/selectable PDF using OCR."""
    print(f"Starting OCR for: {Path(file_path).name}...")
    ocrmypdf.ocr(
        file_path,
        save_path,
        skip_text=True,
        tesseract_pagesegmode=6,
        tesseract_oem=3,
        optimize=1,
        progress_bar=False,
    )
    print(f"File converted successfully and saved to: {Path(save_path).name}")


def _process_ocr_task(task_data: Tuple[Path, Path]) -> Tuple[str, Path, bool]:
    """
    Worker function for parallel OCR processing.

    Args:
        task_data: (original_file_path, output_directory_path)

    Returns:
        Tuple: (original_filename, searchable_path, was_ocr_successful)
    """
    original_file_path, output_path = task_data
    original_name = original_file_path.name

    if not original_file_path.exists():
        return (original_name, original_file_path, False)

    target_path = output_path / original_name

    if _is_pdf_searchable(original_file_path):
        # Already searchable: just copy
        try:
            shutil.copy2(original_file_path, target_path)
            return (original_name, target_path, True)
        except Exception:
            return (original_name, original_file_path, False)
    else:
        # Not searchable: run OCR
        ocr_target_path = output_path / f"OCR_{original_name}"
        try:
            _convert_scanned_pdf(original_file_path, ocr_target_path)
            return (original_name, ocr_target_path, True)
        except Exception as e:
            print(f"ERROR: Failed to OCR {original_name}. Error: {e}")
            # Fallback to original path if OCR fails
            return (original_name, original_file_path, False)

def _classify_file_type(file_path: Path) -> str:
    """Global function to classify file type by examining content."""
    try:
        doc = fitz.open(file_path)
        # Check first page for keywords
        first_page_text = doc[0].get_text("text").lower()
        second_line = first_page_text.splitlines()[1] if len(first_page_text.splitlines()) > 1 else ""
        if "patient results" in second_line:
            return "Lab Results"
        else:
            return "Medical Records"
    except Exception as e:
        print(f"Error classifying {file_path.name}: {e}")
        return "Unknown"


def _process_single_file(file_data: Tuple[str, Path, str]) -> Dict[str, Any]:
    """
    Function executed by each worker process (or sequentially) to run the
    appropriate parsing pipeline. Must be outside the class for multiprocessing.

    Args:
        file_data (Tuple[str, Path, str]): (original_filename, searchable_path, file_type)

    Returns:
        Dict[str, Any]: Dictionary containing the filename, type, and structured data.
    """
    original_filename, searchable_path, file_type = file_data

    try:
        if file_type == "Lab Results":
            parser = LabResultParser()
            structured_data = parser.build_timeline(searchable_path)
        elif file_type == "Medical Records":
            parser = MedicalRecordsParser()
            structured_data = parser.build_timeline(searchable_path)
        else:
            structured_data = {"error": "Unknown file type, skipped parsing."}

        return {
            "original_filename": original_filename,
            "file_type": file_type,
            "structured_data": structured_data,
        }
    except Exception as e:
        return {
            "original_filename": original_filename,
            "file_type": file_type,
            "structured_data": {"error": f"Parsing failed: {e}"},
        }


# --- Main File Processor Class ---
class PDFUploadProcessor:
    """
    A class to process uploaded PDF files.
    1. Convert scanned PDFs to searchable PDFs using OCR.
    2. Classify PDFs into Lab Results or Medical Records.
    3. Extract and parse content from the PDFs.
    4. Combine structured data into a unified patient timeline.

    Attributes:
        input_dir (Path): Directory containing uploaded PDF files.
        output_dir (Path): Directory to save processed searchable PDFs.
        uploaded_files (List[Path]): List of uploaded PDF file paths.
        structured_data_results (List[Dict[str, Any]]): List to store structured data results
    """
    def __init__(self, uploaded_files_directory: str) -> None:
        """
        Initializes the processor.
        """
        self.input_dir = Path(uploaded_files_directory) 
        self.output_dir = self.input_dir / "processed_pdfs"
        
        if not self.input_dir.is_dir():
            raise ValueError(f"The path '{uploaded_files_directory}' is not a valid directory.")
        
        self.uploaded_files = list(self.input_dir.glob("*.pdf")) 
        
        if not self.uploaded_files:
            print(f"Warning: No PDF files found in '{uploaded_files_directory}'.")

        # Removed self.searchable_files
        self.structured_data_results: List[Dict[str, Any]] = []

    def convert_files_to_searchable_pdfs(self, multi: bool = False) -> None:
        """
        Processes all uploaded files, performing OCR if they are not already searchable,
        and saves them to the output directory.
        """
        output_path = self.output_dir 
        output_path.mkdir(parents=True, exist_ok=True)
        # Note: self.searchable_files is no longer populated

        print(f"\n--- Starting OCR Conversion Process (Output Dir: {output_path.resolve()}, Parallel={multi}) ---")
        
        task_data = [(file_path, output_path) for file_path in self.uploaded_files if file_path.exists()]
        
        if multi:
            num_processes = cpu_count()
            print(f"Using {num_processes} worker processes for OCR.")
            with Pool(num_processes) as pool:
                # Run for the side-effect of saving files to disk
                _ = pool.map(_process_ocr_task, task_data)
        else:
            for data in task_data:
                _ = _process_ocr_task(data) # Run for side-effect

        print("--- OCR Conversion Process Complete ---")
        print(f"Files are now available in the output directory ({output_path.name}) for parsing.")


    def extract_and_parse_documents(self, multi: bool = False) -> List[Dict[str, Any]]:
        """
        Classifies, extracts, and parses PDFs by reading files directly from the output directory.
        """
        # Read the files saved in the output directory
        searchable_files_paths = list(self.output_dir.glob("*.pdf"))
        
        if not searchable_files_paths:
            print("Error: The output directory is empty. Run convert_files_to_searchable_pdfs() first.")
            return []

        print(f"\n--- Starting Content Extraction & Parsing (Parallel={multi}) ---")

        # 1. Classification (Using the global function _classify_file_type)
        files_for_classification = [path for path in searchable_files_paths]
        print("Starting Classification...")

        if multi:
            num_processes = cpu_count()
            with Pool(num_processes) as pool:
                classified_types = pool.map(_classify_file_type, files_for_classification)
        else:
            classified_types = [_classify_file_type(path) for path in files_for_classification]

        # 2. Prepare files for Parsing
        files_to_process = []
        for file_path, file_type in zip(files_for_classification, classified_types):
            original_name = file_path.name
            print(f"Classified {original_name} as {file_type}")
            files_to_process.append((original_name, file_path, file_type))

        # 3. Parsing (Using existing global worker _process_single_file)
        if multi:
            num_processes = cpu_count()
            print(f"Starting Parallel Parsing using {num_processes} worker processes.")
            with Pool(num_processes) as pool:
                all_results = pool.map(_process_single_file, files_to_process)
        else:
            all_results = [_process_single_file(file_data) for file_data in files_to_process]

        print("--- Content Extraction & Parsing Complete ---")
        self.structured_data_results = all_results
        return all_results 

    def create_combined_patient_timeline(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Combines the structured JSON outputs from all files into a single chronological 
        timeline, keyed by date, applying the necessary transformations and metadata.
        
        This logic correctly handles the input structure of {date: list_of_raw_records} 
        for both Medical Records and Lab Results, ensuring each event has correct metadata.
        """
        if not self.structured_data_results:
            print("Error: Run extract_and_parse_documents() first to generate structured data.")
            return {} 

        print("\n--- Starting Unified Patient Timeline Creation ---")

        # Unified timeline will map date string -> list of events/records
        unified_timeline: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        
        for result in self.structured_data_results:
            file_type = result.get("file_type")
            structured_data = result.get("structured_data", {})
            original_filename = result.get("original_filename")

            # Skip files with errors or missing data
            if not structured_data or "error" in structured_data:
                print(f"Skipping {original_filename} due to previous parsing error or empty data.")
                continue

            # Iterate over the date keys, where the value is expected to be a list of records
            for date, records_list in structured_data.items():
                
                # Ensure the data structure is a list of records
                if not isinstance(records_list, list):
                    print(f"Warning: Data for {original_filename} on {date} is not a list and was skipped.")
                    continue
                
                for raw_record in records_list:                    
                    if file_type == "Lab Results":
                        # For Lab Results, we add the record under a 'tests' key
                        event = {
                            "record_type": file_type,
                            "source_file": original_filename,
                            # The raw_record is expected to be a dict of lab results
                            "tests": [raw_record]
                        }
                        
                    elif file_type == "Medical Records":
                        # For Medical Records, we merge the raw note data directly into the event
                        event = {
                            "record_type": file_type,
                            "source_file": original_filename,
                            **raw_record 
                        }
                    # Future implementations for other file types can be added here in elif blocks

                    unified_timeline[date].append(event)
            
        final_timeline = dict(unified_timeline)
        
        print("--- Unified Patient Timeline Creation Complete ---")

        # Save the file to the output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
        output_path = self.output_dir / "combined_patient_timeline.json"
        with open(
            output_path, "w", encoding="utf-8"
        ) as f:
            json.dump(final_timeline, f, ensure_ascii=False, indent=4)
        
        print(f"Output saved to: {output_path}")

        return final_timeline


if __name__ == "__main__":
    # Example usage
    flag = True
    start_time = time.time()
    processor = PDFUploadProcessor("../../data/test multi file") # Change to directory with test files
    # processor.convert_files_to_searchable_pdfs(multi=flag)
    processor.extract_and_parse_documents(multi=flag)
    processor.create_combined_patient_timeline()
    end_time = time.time()
    print(f"Total processing time: {end_time - start_time} seconds for multi={flag}")
