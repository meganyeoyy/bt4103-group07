import React, { useEffect, useMemo, useState } from "react";
import Header from "./components/Header";
import TemplateSelect from "./components/TemplateSelect";
import FileUploader from "./components/FileUploader";
import FileList from "./components/FileList";
import SourcePreview from "./components/SourcePreview";
import InsurerForm from "./components/InsurerForm";
import { fieldsToOverlays } from "./utils/overlays";

const BASE_URL = "https://unplundered-greatheartedly-sharleen.ngrok-free.dev";
const POLL_INTERVAL_MS = 30000;
const NGROK_HEADERS = { "ngrok-skip-browser-warning": "true" };
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

export default function App() {
  const [template, setTemplate] = useState("");
  const [files, setFiles] = useState([]);
  const [selected, setSelected] = useState("");
  const [overlaysB64, setOverlaysB64] = useState("");
  const [counts, setCounts] = useState({ low: 0, missing: 0 });
  const [isGenerating, setIsGenerating] = useState(false);
  const [showSource, setShowSource] = useState(true);
  const [generatedPdfUrl, setGeneratedPdfUrl] = useState("");

  // Cleanup generated blob URL on change/unmount
  useEffect(() => {
    return () => {
      if (generatedPdfUrl) URL.revokeObjectURL(generatedPdfUrl);
    };
  }, [generatedPdfUrl]);

  // Clear generated PDF when switching selected file
  useEffect(() => {
    if (generatedPdfUrl) {
      URL.revokeObjectURL(generatedPdfUrl);
      setGeneratedPdfUrl("");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selected]);

  // Load overlay coordinates for insurer template
  useEffect(() => {
    let alive = true;

    (async () => {
      if (!template) {
        setOverlaysB64("");
        setCounts({ low: 0, missing: 0 });
        return;
      }

      try {
        const map = {
          "NTUC Income": "/overlays/income.json",
          Prudential: "/overlays/prudential.json",
        };
        const url = map[template];
        if (!url) {
          if (alive) {
            setOverlaysB64("");
            setCounts({ low: 0, missing: 0 });
          }
          return;
        }

        const resp = await fetch(
          `${url}?v=${Date.now().toString().slice(0, 7)}`
        );
        if (!resp.ok)
          throw new Error(`Failed to fetch overlays: ${resp.status}`);
        const data = await resp.json();
        if (!alive) return;

        const items = fieldsToOverlays(data);
        setOverlaysB64(btoa(JSON.stringify(items)));

        const low = items.filter((it) => it.class === "low").length;
        const missing = items.filter((it) => it.class === "missing").length;
        setCounts({ low, missing });
      } catch (e) {
        console.warn("Overlay load failed:", e);
        if (alive) {
          setOverlaysB64("");
          setCounts({ low: 0, missing: 0 });
        }
      }
    })();

    return () => {
      alive = false;
    };
  }, [template]);

  /* ------------------------ File Handling ------------------------ */
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
    if (fileToRemove) {
      URL.revokeObjectURL(fileToRemove.url); // ✅ revoke only this one
    }

    const next = files.filter((f) => f.name !== name);
    setFiles(next);
    if (selected === name) setSelected(next[0]?.name ?? "");
  };

  // ✅ Cleanup only on unmount (no dependency)
  useEffect(() => {
    return () => {
      files.forEach((f) => URL.revokeObjectURL(f.url));
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const selectedFile = useMemo(
    () => files.find((f) => f.name === selected) || null,
    [files, selected]
  );

  /* ------------------------ JSON helper ------------------------ */
  const readJsonOrThrow = async (resp, contextForErrors) => {
    const body = await resp.text();
    try {
      return JSON.parse(body);
    } catch {
      const preview = body.length > 500 ? body.slice(0, 500) + " …" : body;
      throw new Error(`Non-JSON ${contextForErrors} response: ${preview}`);
    }
  };

  /* ------------------------ Generate Handler ------------------------ */
  const handleGenerate = async () => {
    if (isGenerating) return;
    if (!selectedFile?.fileObj) {
      alert("Please select a file to generate.");
      return;
    }

    setIsGenerating(true);

    if (generatedPdfUrl) {
      URL.revokeObjectURL(generatedPdfUrl);
      setGeneratedPdfUrl("");
    }

    try {
      // 0) Health check
      let healthResp;
      try {
        healthResp = await fetch(
          `${BASE_URL}/health?ngrok-skip-browser-warning=true`,
          { method: "GET" }
        );
      } catch {
        throw new Error(
          "Cannot reach backend (/health). Is Colab/ngrok running and BASE_URL current?"
        );
      }
      if (!healthResp.ok) {
        const txt = await healthResp.text().catch(() => "");
        throw new Error(`Health check failed: ${healthResp.status} ${txt}`);
      }

      // 1) Upload file
      const formData = new FormData();
      const file = selectedFile.fileObj;
      const filename = file.name || selectedFile.name || "document.pdf";
      formData.append("file", file, filename);

      let askResp;
      try {
        askResp = await fetch(`${BASE_URL}/ask`, {
          method: "POST",
          headers: NGROK_HEADERS,
          body: formData,
        });
      } catch {
        throw new Error("Network error reaching /ask (CORS/tunnel).");
      }

      if (!askResp.ok) {
        const text = await askResp.text().catch(() => "");
        throw new Error(`Upload failed (${askResp.status}) ${text}`);
      }

      const askJson = await readJsonOrThrow(askResp, "/ask");
      const job_id = askJson.job_id;
      if (!job_id) throw new Error("No job_id returned from /ask");
      console.log("Job submitted:", job_id);

      // 2) Poll result
      let status = "pending";
      let lastError = "";
      while (status !== "completed" && status !== "error") {
        let res;
        try {
          res = await fetch(`${BASE_URL}/result/${job_id}`, {
            method: "GET",
            headers: NGROK_HEADERS,
          });
        } catch {
          throw new Error("Network error reaching /result (CORS/tunnel).");
        }

        if (!res.ok) {
          const text = await res.text().catch(() => "");
          throw new Error(`Result poll failed (${res.status}) ${text}`);
        }

        const job = await readJsonOrThrow(res, "/result");
        status = job.status;
        lastError = job.result || job.error || "";
        console.log("Status:", status);

        if (status === "completed") break;
        if (status === "error")
          throw new Error(lastError || "Unknown backend error");

        await sleep(POLL_INTERVAL_MS);
      }

      // 3) Download filled PDF
      let pdfRes;
      try {
        pdfRes = await fetch(`${BASE_URL}/download/${job_id}`, {
          method: "GET",
          headers: NGROK_HEADERS,
        });
      } catch {
        throw new Error("Network error reaching /download (CORS/tunnel).");
      }

      if (!pdfRes.ok) {
        const text = await pdfRes.text().catch(() => "");
        throw new Error(`Download failed (${pdfRes.status}) ${text}`);
      }

      const blob = await pdfRes.blob();
      const url = URL.createObjectURL(blob);
      setGeneratedPdfUrl(url);

      const link = document.createElement("a");
      link.href = url;
      link.download = `filled_${job_id}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();

      alert("Generated PDF downloaded successfully!");
    } catch (err) {
      console.error("Error during backend processing:", err);
      const message =
        typeof err?.message === "string"
          ? err.message
          : "Backend processing failed.";
      alert(`Backend processing failed: ${message}`);
    } finally {
      setIsGenerating(false);
    }
  };

  /* ------------------------ Render ------------------------ */
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
          overlaysB64={overlaysB64}
          generatedPdfUrl={generatedPdfUrl}
          isGenerating={isGenerating}
        />
      </div>
    </div>
  );
}
