document.addEventListener("DOMContentLoaded", async () => {
  const result = (await browser.storage.local.get("currentResumeHtml")) as any;
  const html = result?.currentResumeHtml as string;

  if (!html) {
    document.body.innerHTML = `
      <div style="padding: 40px; text-align: center; font-family: sans-serif; color: #a1a1aa;">
        <h2>No resume preview available</h2>
        <p>Please generate a resume from the extension popup first.</p>
      </div>
    `;
    return;
  }

  const iframe = document.getElementById("previewFrame") as HTMLIFrameElement;
  if (iframe) {
    iframe.addEventListener("load", () => {
      enablePreviewEditing(iframe);
      updateOverflowWarning(iframe);
      window.setTimeout(() => updateOverflowWarning(iframe), 250);
    });
    iframe.srcdoc = html;
  }

  const getEditedHtml = () => {
    if (iframe && iframe.contentDocument) {
      // Clone document to strip editing markers before copying or downloading
      const docClone = iframe.contentDocument.cloneNode(true) as Document;
      const editableElements = docClone.querySelectorAll("[contenteditable]");
      editableElements.forEach((el) => {
        el.removeAttribute("contenteditable");
      });
      docClone.querySelectorAll(".page.overflowing").forEach((page) => {
        page.classList.remove("overflowing");
      });
      return "<!DOCTYPE html>\n" + docClone.documentElement.outerHTML;
    }
    return html;
  };

  const copyBtn = document.getElementById("copyBtn");
  if (copyBtn) {
    copyBtn.addEventListener("click", () => {
      const activeHtml = getEditedHtml();
      navigator.clipboard.writeText(activeHtml).then(() => {
        copyBtn.textContent = "Copied!";
        copyBtn.style.background = "#10b981";
        copyBtn.style.color = "#fff";
        setTimeout(() => {
          copyBtn.textContent = "Copy HTML";
          copyBtn.style.background = "";
          copyBtn.style.color = "";
        }, 2000);
      });
    });
  }

  const downloadBtn = document.getElementById("downloadBtn");
  if (downloadBtn) {
    downloadBtn.addEventListener("click", () => {
      const activeHtml = getEditedHtml();
      const blob = new Blob([activeHtml], { type: "text/html" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "tailored-resume.html";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    });
  }

  const printBtn = document.getElementById("printBtn");
  if (printBtn) {
    printBtn.addEventListener("click", () => {
      if (iframe && iframe.contentWindow) {
        if (iframe.contentDocument && iframe.contentDocument.activeElement) {
          (iframe.contentDocument.activeElement as HTMLElement).blur();
        }
        clearOverflowMarkers(iframe);
        iframe.contentWindow.addEventListener(
          "afterprint",
          () => updateOverflowWarning(iframe),
          { once: true },
        );
        iframe.contentWindow.focus();
        iframe.contentWindow.print();
      }
    });
  }
});

function enablePreviewEditing(iframe: HTMLIFrameElement) {
  const page = iframe.contentDocument?.querySelector(".page");
  if (!(page instanceof HTMLElement)) return;

  page.setAttribute("contenteditable", "true");
  page.setAttribute("spellcheck", "false");
  page.addEventListener("input", () => updateOverflowWarning(iframe));
}

function clearOverflowMarkers(iframe: HTMLIFrameElement) {
  iframe.contentDocument
    ?.querySelectorAll(".page.overflowing")
    .forEach((page) => {
      page.classList.remove("overflowing");
    });
  document.body.classList.remove("has-overflow");
}

function updateOverflowWarning(iframe: HTMLIFrameElement) {
  const page = iframe.contentDocument?.querySelector(".page");
  if (!(page instanceof HTMLElement)) return;

  const hasOverflow = page.scrollHeight > page.clientHeight + 1;
  page.classList.toggle("overflowing", hasOverflow);
  document.body.classList.toggle("has-overflow", hasOverflow);
}
