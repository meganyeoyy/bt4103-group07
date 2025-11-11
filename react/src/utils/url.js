export function absoluteUrl(pathOrUrl) {
  try {
    const u = new URL(pathOrUrl);
    return u.toString();
  } catch {
    return new URL(pathOrUrl, window.location.origin).toString();
  }
}

export function buildViewerSrc(pdfPathOrUrl) {
  const qs = new URLSearchParams();
  qs.set("file", absoluteUrl(pdfPathOrUrl));
  return `/pdfjs5/web/viewer.html?${qs.toString()}`;
}
