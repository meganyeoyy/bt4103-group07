import React, { useEffect, useMemo, useState } from "react";
import Header from "./components/Header";
import TemplateSelect from "./components/TemplateSelect";
import FileUploader from "./components/FileUploader";
import FileList from "./components/FileList";
import SourcePreview from "./components/SourcePreview";
import InsurerForm from "./components/InsurerForm";
import { fieldsToOverlays } from "./utils/overlays";

const BASE_URL = "https://unplundered-greatheartedly-sharleen.ngrok-free.dev";
const POLL_INTERVAL_MS = 20000; // poll every 20s
const NGROK_HEADERS = { "ngrok-skip-browser-warning": "true" };
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

export default function App() {
  const [template, setTemplate] = useState("");
  const [files, setFiles] = useState([]);
  const [selected, setSelected] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const [showSource, setShowSource] = useState(true);
  const [generatedPdfUrl, setGeneratedPdfUrl] = useState("");
  const [filledJson, setFilledJson] = useState(null);
  const [counts, setCounts] = useState({ low: 0, missing: 0 });

  // cleanup blob URLs on unmount
  useEffect(() => {
    return () => {
      if (generatedPdfUrl) {
        URL.revokeObjectURL(generatedPdfUrl);
      }
    };
  }, [generatedPdfUrl]); // 👈 only depends on generatedPdfUrl

  const selectedFile = useMemo(
    () => files.find((f) => f.name === selected) || null,
    [files, selected]
  );

  const addFiles = (newFiles) => {
    const pdfs = [...newFiles].filter(
      (f) =>
        f.type === "application/pdf" || f.name.toLowerCase().endsWith(".pdf")
    );
    const mapped = pdfs.map((f) => ({
      name: f.name,
      type: "PDF",
      url: URL.createObjectURL(f),
      fileObj: f,
    }));

    const next = [...files, ...mapped];
    setFiles(next);
    if (!selected && next.length) setSelected(next[0].name);
  };

  const removeFile = (name) => {
    const fileToRemove = files.find((f) => f.name === name);
    if (fileToRemove) URL.revokeObjectURL(fileToRemove.url);

    const next = files.filter((f) => f.name !== name);
    setFiles(next);
    if (selected === name) setSelected(next[0]?.name ?? "");
  };

  // helper for parsing JSON safely
  const readJsonOrThrow = async (resp, contextForErrors) => {
    const body = await resp.text();
    try {
      return JSON.parse(body);
    } catch {
      const preview = body.length > 500 ? body.slice(0, 500) + " …" : body;
      throw new Error(`Non-JSON ${contextForErrors} response: ${preview}`);
    }
  };

  const handleGenerate = async () => {
    if (isGenerating) return;
    if (!selectedFile?.fileObj || !template) {
      alert("Please select both an input file and an insurer template.");
      return;
    }

    setIsGenerating(true);
    setGeneratedPdfUrl("");
    setFilledJson(null);

    try {
      // Health check
      const health = await fetch(`${BASE_URL}/health`, {
        method: "GET",
        headers: NGROK_HEADERS,
      });
      if (!health.ok) throw new Error("Backend not reachable.");

      // Prepare form data for multiple uploaded files
      const formData = new FormData();
      if (!files.length) {
        alert("Please upload at least one input PDF.");
        setIsGenerating(false);
        return;
      }

      // append all uploaded files under the key 'input_pdfs'
      files.forEach((f) => {
        formData.append("input_pdfs", f.fileObj, f.name);
      });

      // insurer template PDF (from /templates folder)
      const templateMap = {
        "NTUC Income": "/templates/income.pdf",
        "Great Eastern": "/templates/ge.pdf",
      };
      const templateFileNames = {
        "NTUC Income": "income.pdf",
        "Great Eastern": "ge.pdf",
      };
      const templateUrl = templateMap[template];
      if (!templateUrl) throw new Error("Invalid or missing template PDF.");
      const templateResp = await fetch(templateUrl);
      const templateBlob = await templateResp.blob();
      formData.append(
        "template_pdf",
        templateBlob,
        templateFileNames[template]
      );

      // insurer field coordinates JSON
      const overlayMap = {
        "NTUC Income": "/overlays/income.json",
        "Great Eastern": "/overlays/ge.json",
      };
      const overlayUrl = overlayMap[template];
      const overlayResp = await fetch(overlayUrl);
      const overlayBlob = await overlayResp.blob();
      formData.append("form_fields_json", overlayBlob, "form_fields.json");

      // Send to backend
      const askResp = await fetch(`${BASE_URL}/ask`, {
        method: "POST",
        headers: NGROK_HEADERS,
        body: formData,
      });
      if (!askResp.ok)
        throw new Error(
          `Upload failed (${askResp.status}) ${await askResp.text()}`
        );
      const { job_id } = await readJsonOrThrow(askResp, "/ask");
      if (!job_id) throw new Error("No job_id returned from backend.");
      console.log("Job submitted:", job_id);

      // Poll for result
      let status = "pending";
      let jobData = null;
      while (status === "pending") {
        const res = await fetch(`${BASE_URL}/result/${job_id}`, {
          method: "GET",
          headers: NGROK_HEADERS,
        });
        if (!res.ok)
          throw new Error(
            `Result poll failed (${res.status}) ${await res.text()}`
          );
        jobData = await readJsonOrThrow(res, "/result");
        status = jobData.status;
        if (status === "pending") {
          await sleep(POLL_INTERVAL_MS);
        } else if (status === "error") {
          throw new Error(jobData.error || "Unknown backend error.");
        }
      }

      // Parse results
      const { pdf_b64, form_fields_filled } = jobData;
      if (!pdf_b64) throw new Error("Missing PDF output in backend response.");

      // create PDF blob URL
      const blob = new Blob(
        [Uint8Array.from(atob(pdf_b64), (c) => c.charCodeAt(0))],
        { type: "application/pdf" }
      );
      const url = URL.createObjectURL(blob);
      setGeneratedPdfUrl(url);

      // parse JSON → overlay display
      const items = fieldsToOverlays(form_fields_filled);
      setFilledJson(form_fields_filled);
      setCounts({
        low: items.filter((it) => it.class === "low").length,
        missing: items.filter((it) => it.class === "missing").length,
      });

      alert("Processing completed successfully!");
    } catch (err) {
      console.error("Error during backend processing:", err);
      alert(`Backend processing failed: ${err.message || "Unknown error"}`);
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="app">
      <Header
        docs={files.length}
        templateLabel={template || "No template selected"}
        lowConf={counts.low}
        missing={counts.missing}
      />

      <div className="card section">
        <div className="uploadGrid">
          <div>
            <FileUploader onFiles={addFiles} />
          </div>

          <div className="fill">
            <div style={{ fontWeight: 700, marginBottom: 8 }}>
              Files in this case
            </div>
            <FileList
              files={files}
              selected={selected}
              onSelect={setSelected}
              onRemove={removeFile}
            />
          </div>
        </div>
      </div>

      <div className="templateRow">
        <div className="templateLeft">
          <TemplateSelect value={template} onChange={setTemplate} />
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "20px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <span style={{ fontWeight: 600 }}>Hide Source Preview</span>
            <label className="toggle-switch">
              <input
                type="checkbox"
                checked={!showSource}
                onChange={() => setShowSource((prev) => !prev)}
              />
              <span className="slider"></span>
            </label>
          </div>

          <button
            className={`btn ${isGenerating ? "loading" : ""}`}
            onClick={handleGenerate}
            disabled={isGenerating}
          >
            {isGenerating && (
              <span className="spinner" style={{ marginRight: 8 }}></span>
            )}
            {isGenerating ? "Generating..." : "Generate"}
          </button>
        </div>
      </div>

      <div className={`grid ${showSource ? "with-source" : "no-source"}`}>
        {showSource && <SourcePreview file={selectedFile} />}
        <InsurerForm
          overlaysB64={
            filledJson ? btoa(JSON.stringify(fieldsToOverlays(filledJson))) : ""
          }
          generatedPdfUrl={generatedPdfUrl}
          isGenerating={isGenerating}
        />
      </div>
    </div>
  );
}
