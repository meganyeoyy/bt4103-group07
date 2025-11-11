(function () {
  // DOM helpers
  function ensureHud(pageDiv) {
    let hud = pageDiv.querySelector(".pdf-hud-layer");
    if (!hud) {
      hud = document.createElement("div");
      hud.className = "pdf-hud-layer";
      hud.style.position = "absolute";
      hud.style.pointerEvents = "none";
      pageDiv.appendChild(hud);
    }
    return hud;
  }

  function getCanvasBox(pageView) {
    const pageDiv = pageView.div;
    const wrapper =
      pageDiv.querySelector(".canvasWrapper") ||
      pageDiv.firstElementChild ||
      pageDiv;
    return {
      wrapper,
      left: wrapper.offsetLeft,
      top: wrapper.offsetTop,
      w: wrapper.clientWidth,
      h: wrapper.clientHeight,
    };
  }

  // Render
  function renderPage(items, pageView) {
    if (!pageView || !pageView.div) return;

    const hud = ensureHud(pageView.div);
    hud.innerHTML = "";

    const box = getCanvasBox(pageView);

    // Pin HUD to the exact canvas wrapper
    hud.style.left = box.left + "px";
    hud.style.top = box.top + "px";
    hud.style.width = box.w + "px";
    hud.style.height = box.h + "px";

    // Track current zoom scale from pdf.js
    const s =
      (window.PDFViewerApplication &&
        window.PDFViewerApplication.pdfViewer &&
        window.PDFViewerApplication.pdfViewer.currentScale) ||
      1;

    for (const it of items) {
      if (it.page !== pageView.id) continue;
      if (typeof it.xPct !== "number" || typeof it.yPct !== "number") continue;

      const x = (it.xPct / 100) * box.w;
      const y = (it.yPct / 100) * box.h;

      const chip = document.createElement("div");
      chip.className = `pdf-hud-chip ${it.class || ""}`.trim();
      chip.textContent = it.label || "Missing";
      chip.style.left = `${x}px`;
      chip.style.top = `${y}px`;
      chip.style.setProperty("--pdf-scale", String(s));

      hud.appendChild(chip);
    }
  }

  // Throttle redraws during viewport changes
  let rafToken = null;
  function scheduleRedrawVisible(items, app) {
    if (rafToken) return;
    rafToken = requestAnimationFrame(() => {
      rafToken = null;
      const vis = app?.pdfViewer?._getVisiblePages?.().views || [];
      for (const v of vis) renderPage(items, v.view || v);
    });
  }

  // State
  let items = [];
  function setItems(next, app) {
    items = Array.isArray(next) ? next : [];
    const vis = app?.pdfViewer?._getVisiblePages?.().views || [];
    for (const v of vis) renderPage(items, v.view || v);
  }

  // Boot
  async function main() {
    while (
      !(
        window.PDFViewerApplication &&
        window.PDFViewerApplication.eventBus &&
        window.PDFViewerApplication.pdfViewer
      )
    ) {
      await new Promise((r) => setTimeout(r, 50));
    }

    const app = window.PDFViewerApplication;
    const bus = app.eventBus;

    scheduleRedrawVisible(items, app);

    // Re-render when a page finishes (initial render / zoom / rotate)
    bus.on("pagerendered", (evt) => renderPage(items, evt.source));

    // Viewport updates (scroll/zoom)
    bus.on("updateviewarea", () => scheduleRedrawVisible(items, app));

    // Runtime updates from parent via postMessage
    window.addEventListener("message", (e) => {
      const msg = e?.data;
      if (!msg || typeof msg !== "object") return;
      if (msg.type === "apply-overlays" && Array.isArray(msg.overlays)) {
        setItems(msg.overlays, app);
      } else if (msg.type === "clear-overlays") {
        setItems([], app);
      }
    });

    try {
      window.parent?.postMessage({ type: "overlay-ready" }, "*");
    } catch {}
  }

  main();
})();
