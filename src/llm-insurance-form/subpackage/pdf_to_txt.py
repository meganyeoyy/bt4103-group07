import os
import time
from pdf2image import convert_from_path
import pytesseract

# on terminal install poppler to use pdf2image: `brew install poppler`
# on terminal install tesseract to use pytesseract: `brew install tesseract`

# to run file: `python pdf_to_txt.py`

# pdf_file = "Redacted - LHS R.pdf" (38.64 seconds)
# pdf_file = "Redacted - LHS SCM.pdf" (110.11 seconds)

def pdf_to_txt(file_path):
    print(f"Extract text from pdf: {file_path}")
    start_time = time.time()  # start timer
    # Convert PDF to images
    pages = convert_from_path(file_path)

    # Extract text
    text = ""
    for page in pages:
        text += pytesseract.image_to_string(page)

    # Define output folder
    output_folder = "/Users/meganyeo/Desktop/y4s1/capstone/data/raw-txt"
    os.makedirs(output_folder, exist_ok=True)

    # Create output file name with same base name as PDF
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    txt_file = os.path.join(output_folder, base_name + ".txt")

    # Write to text file
    with open(txt_file, "w", encoding="utf-8") as f:
        f.write(text)

    end_time = time.time()  # end timer
    elapsed_time = end_time - start_time

    print(f"Text extracted and saved to {txt_file}")
    print(f"Execution time: {elapsed_time:.2f} seconds")

# Folder containing PDFs
input_folder = os.path.join(os.path.dirname(__file__), "../../../data/pdf")

# Get a list of all PDF files
pdf_files = [f for f in os.listdir(input_folder) if f.lower().endswith(".pdf")]

# Loop over each PDF file
for pdf_file in pdf_files:
    pdf_path = os.path.join(input_folder, pdf_file)
    pdf_to_txt(pdf_path)

