# bt4103-group07 : LLM Insurance Form Filler
This project is a full-stack application designed to automate the process of filling out insurance forms using a Large Language Model (LLM). It consists of a React frontend for user interaction and a Python-based backend pipeline that runs on Google Colab to handle data processing and model inference. The system allows users to upload patient medical records, which are then processed by an LLM to automatically extract and fill in the required fields on a target insurance form.

## Demo

A full video walkthrough of the frontend experience, "from uploading documents to generating insurer forms," is available on YouTube. The demo showcases file uploads, insurer selection, real-time generation feedback, and result validation.

* **[Watch Demo on YouTube](https://www.youtube.com/watch?v=-klqTYrpS6A)** 

---

## Codebase Structure

The project is organized into three main top-level directories:

1.  **/data**: Contains all static assets, including raw patient files, blank form templates, and ground-truth evaluation data.
2.  **/react**: Contains the complete source code for the user-facing React frontend application.
3.  **/src**: Contains the complete source code for the backend Python pipeline (named `llm-insurance-form`), which handles all data processing and model inference.

### 1. `/data` Directory

This directory stores all non-code assets needed for the pipeline to run and for its results to be evaluated.

* `/data/eval/`: Contains ground-truth JSON files (e.g., `ntuc_gt_patient_1.json`) used by `evaluation.py` to score the LLM's accuracy.
* `/data/Lab Results/` & `/data/SCM Records/`: Store raw, redacted patient medical records in PDF format.
* `/data/pdf/`: Contains the blank insurance forms (e.g., `ntuc_form.pdf`) that the pipeline fills.
* `/data/templates/`: A critical folder containing JSON "field templates" (e.g., `ge_form_fields_empty.json`). These define the exact JSON structure the `fill_form.py` script expects.

### 2. `/react` Directory (Frontend)

This directory holds the entire React-based frontend application.

* `/react/public/`: Contains static assets for the web app.
    * `/public/overlays/`: JSON files (e.g., `ge.json`) that define the (x, y) coordinates for rendering data onto the PDF templates in the frontend viewer.
    * `/public/pdfjs5/`: A vendored copy of the PDF.js library for rendering PDFs in the browser.
    * `/public/templates/`: Blank PDF files (e.g., `ge.pdf`) shown to the user in the frontend.
* `/react/src/`: Contains the React application's source code.
    * `/src/App.js`: The main application component that orchestrates the flow.
    * `/src/components/`: Directory for reusable React components, such as `FileUploader.jsx`, `InsurerForm.jsx`, and `SourcePreview.jsx`.
    * `/src/utils/`: Utility scripts for the frontend, including `overlays.js` and `url.js` (for managing backend API endpoint URLs).

### 3. `/src/llm-insurance-form` (Backend)

This is the core Python package containing the entire data processing and AI pipeline.

* `backend_deployment.ipynb`: A Jupyter Notebook used to deploy and run the entire backend pipeline on Google Colab (with a T4 GPU). It contains setup, model loading, and the Flask server initiation with ngrok.
* `main.py`: The main entry point for the Flask web server. It defines the API endpoints (e.g., `/upload`, `/process`) that the React frontend calls.
* `/evaluation/evaluation.py`: Compares the LLM's final JSON output against the ground-truth JSON to calculate accuracy metrics.
* `/fill-form/fill_form.py`: A script that takes the final, mapped JSON and programmatically fills in the blank PDF template.
* `/llm/llm.py`: Contains the logic to load the model (e.g., Phi-4) and execute the inference call.
* `/llm/prompts/`: Contains the prompt templates, logically split by form type and page (e.g., `page-1.txt`), that guide the LLM's extraction.
* `/medical-files-processing/`: The pre-processing module.
    * `document_parser.py`: Extracts text and metadata from the raw patient PDFs.
    * `file_upload_processor.py`: Manages the ingestion of multiple files and creates a unified patient timeline.
* `/post-processing/`: A crucial module that cleans and maps the LLM's raw output.
    * `post-processing.py`: (Stage 1) Cleans the raw JSON from the LLM, repairs errors, and flattens multiple page-based JSONs into a single dictionary.
    * `make_final_json.py`: (Stage 2) Maps the clean, flattened JSON to the final PDF template schema from `/data/templates/`.
* `/rag/rag.py`: The Retrieval-Augmented Generation module. It retrieves the most relevant text chunks to be injected into the LLM prompt.
* **Configuration**: The backend pipeline uses YAML configuration files (e.g., `llm-config.yml`, `rag_config.yml`) for each module, allowing parameters like model names or file paths to be modified without changing the source code.

---

## Getting Started: Developer Setup

This project requires running two components simultaneously: the **Backend** on Google Colab and the **Frontend** on your local machine.

### 1. Backend (Google Colab)

1.  Open the notebook `src/llm-insurance-form/backend_deployment.ipynb` in Google Colab.
2.  Ensure the runtime is set to use a **T4 GPU**.
3.  Run the notebook cells to install dependencies, load the models, and start the Flask server.
4.  The server will use `ngrok` to create a public-facing URL. Note this URL for the frontend setup.

### 2. Frontend (Local)

**Requirements**:
* Node.js 18+
* npm or pnpm
* Internet access to the ngrok-connected backend

**Environment Configuration**:
Before starting the React app, you must configure the environment variables. The key variable is:

* `BASE_URL`: Set this to the `ngrok` backend endpoint URL (e.g., `https://unplundered-greatheartedly-sharleen.ngrok-free.dev`).

You may also need to set `NGROK_HEADERS` to `{"ngrok-skip-browser-warning": "true"}` to suppress tunnel warnings.

**Setup Instructions**:

1.  Clone the repository and navigate to the `react` directory:
    ```bash
    git clone <repo-link>
    cd react
    ```
   
2.  Install dependencies:
    ```bash
    npm install
    ```
   
3.  Start the development server:
    ```bash
    npm run dev
    ```
   
4.  To build for production, run:
    ```bash
    npm run build
    ```
   

---

## Configuration & Tuning

The application can be tuned in several key places:

* **Confidence Threshold (Frontend)**: The confidence threshold for tagging fields as low-confidence can be adjusted in `react/src/utils/overlays.js` by modifying `const CONF_THRESHOLD = 0.9;`. A higher value (e.g., 0.95) will flag more fields, while a lower value (e.g., 0.8) makes detection more lenient.
* **Polling Interval (Frontend)**: The polling frequency for backend results can be adjusted by changing `POLL_INTERVAL_MS` in `react/src/App.js`.
* **Backend Parameters (Backend)**: Backend modules (LLM, RAG) can be configured via their respective `.yml` files (e.g., `llm-config.yml`). This allows for changing model names or file paths without editing the Python code.

Other configuration files can be found in the repositiory for the different components.