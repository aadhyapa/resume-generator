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
      docClone.querySelectorAll("[spellcheck]").forEach((el) => {
        el.removeAttribute("spellcheck");
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
  const doc = iframe.contentDocument;
  const page = doc?.querySelector(".page");
  if (!doc || !(page instanceof HTMLElement)) return;

  doc.designMode = "on";
  doc.documentElement.setAttribute("contenteditable", "true");
  doc.body.setAttribute("contenteditable", "true");
  doc.body.setAttribute("spellcheck", "false");
  page.setAttribute("contenteditable", "true");
  page.setAttribute("spellcheck", "false");
  page.tabIndex = 0;
  page.focus();
  page.addEventListener("input", () => {
    updateOverflowWarning(iframe);
    syncEditsToStorage(iframe);
  });
  doc.addEventListener("input", () => {
    updateOverflowWarning(iframe);
    syncEditsToStorage(iframe);
  });
  doc.addEventListener("click", (event) => {
    if ((event.target as Element | null)?.closest("a")) event.preventDefault();
  });
}

async function syncEditsToStorage(iframe: HTMLIFrameElement) {
  const doc = iframe.contentDocument;
  if (!doc) return;

  const result = (await browser.storage.local.get("generationState")) as any;
  const generationState = result?.generationState;
  if (!generationState || !generationState.resumeData) return;

  const resumeData = JSON.parse(JSON.stringify(generationState.resumeData));

  // Build a map of bullet edits from the DOM
  const bulletElements = doc.querySelectorAll("li[data-bullet-id]");
  const bulletMap: Record<string, { text: string; bold_words: string[] }> = {};

  bulletElements.forEach((el) => {
    const bulletId = el.getAttribute("data-bullet-id");
    if (!bulletId) return;

    const text = el.textContent || "";
    const boldTags = el.querySelectorAll("b, strong");
    const boldWords = Array.from(boldTags)
      .map((node) => node.textContent?.trim() || "")
      .filter(Boolean);

    bulletMap[bulletId] = { text, bold_words: boldWords };
  });

  // Traverse and update resumeData
  let changed = false;
  for (const key in resumeData) {
    if (typeof resumeData[key] === "object" && resumeData[key] !== null) {
      const section = resumeData[key] as any;
      if (section.sub_sections) {
        for (const subId in section.sub_sections) {
          const subSection = section.sub_sections[subId];
          if (Array.isArray(subSection.bullets)) {
            subSection.bullets = subSection.bullets.map((bullet: any) => {
              const bulletId = bullet.bullet_id;
              if (bulletMap[bulletId]) {
                const newText = bulletMap[bulletId].text;
                const newBoldWords = bulletMap[bulletId].bold_words;
                
                const hasTextChange = bullet.text !== newText;
                const hasBoldChange =
                  !bullet.bold_words ||
                  bullet.bold_words.length !== newBoldWords.length ||
                  newBoldWords.some((w: string) => !bullet.bold_words.includes(w));

                if (hasTextChange || hasBoldChange) {
                  changed = true;
                  return {
                    ...bullet,
                    text: newText,
                    bold_words: newBoldWords,
                    edited: true,
                  };
                }
              }
              return bullet;
            });
          }
        }
      }
    }
  }

  if (changed) {
    await browser.storage.local.set({
      generationState: {
        ...generationState,
        resumeData,
      },
    });
  }

  // Also keep currentResumeHtml in sync
  await browser.storage.local.set({
    currentResumeHtml: "<!DOCTYPE html>\n" + doc.documentElement.outerHTML,
  });
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
