import requests
import time
import os
from pathlib import Path


BASE_URL = "https://yukiko-wreathless-helpfully.ngrok-free.dev"


# --- Step 1. Upload multiple PDFs as one job ---
pdf_paths = [
    Path("data/SCM Records/NTUC_Redacted - Patient 1 SCM.pdf")
]

# Build list of ("file", (filename, file_object, mime_type)) tuples
files = [("file", (path.name, open(path, "rb"), "application/pdf")) for path in pdf_paths]

res = requests.post(f"{BASE_URL}/ask", files=files, verify=False)
res.raise_for_status()

job_id = res.json().get("job_id")
print("Job submitted:", job_id)

# Step 2. Poll until done
while True:
    r = requests.get(f"{BASE_URL}/result/{job_id}", verify=False)
    job = r.json()
    print("Status:", job["status"])
    if job["status"] == "completed":
        print("Done - Downloading filled PDF...\n")
        # Step 3. Download the PDF file
        pdf_response = requests.get(f"{BASE_URL}/download/{job_id}", verify=False)
        if pdf_response.status_code == 200:
            output_filename = f"filled_{job_id}.pdf"
            with open(output_filename, "wb") as f:
                f.write(pdf_response.content)
            print(f"Saved to {os.path.abspath(output_filename)}")
        else:
            print("Failed to download PDF:", pdf_response.text)
        break
    elif job["status"] == "error":
        print("Error:", job["result"])
        break
    time.sleep(30)
