document.addEventListener('DOMContentLoaded', async () => {
  const result = await browser.storage.local.get('currentResumeHtml') as any;
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

  const iframe = document.getElementById('previewFrame') as HTMLIFrameElement;
  if (iframe) {
    iframe.srcdoc = html;
  }

  const getEditedHtml = () => {
    if (iframe && iframe.contentDocument) {
      // Clone document to strip editing markers before copying or downloading
      const docClone = iframe.contentDocument.cloneNode(true) as Document;
      const editableElements = docClone.querySelectorAll('[contenteditable]');
      editableElements.forEach((el) => {
        el.removeAttribute('contenteditable');
      });
      return '<!DOCTYPE html>\n' + docClone.documentElement.outerHTML;
    }
    return html;
  };

  const copyBtn = document.getElementById('copyBtn');
  if (copyBtn) {
    copyBtn.addEventListener('click', () => {
      const activeHtml = getEditedHtml();
      navigator.clipboard.writeText(activeHtml).then(() => {
        copyBtn.textContent = 'Copied!';
        copyBtn.style.background = '#10b981';
        copyBtn.style.color = '#fff';
        setTimeout(() => {
          copyBtn.textContent = 'Copy HTML';
          copyBtn.style.background = '';
          copyBtn.style.color = '';
        }, 2000);
      });
    });
  }

  const downloadBtn = document.getElementById('downloadBtn');
  if (downloadBtn) {
    downloadBtn.addEventListener('click', () => {
      const activeHtml = getEditedHtml();
      const blob = new Blob([activeHtml], { type: 'text/html' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'tailored-resume.html';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    });
  }

  const printBtn = document.getElementById('printBtn');
  if (printBtn) {
    printBtn.addEventListener('click', () => {
      if (iframe && iframe.contentWindow) {
        if (iframe.contentDocument && iframe.contentDocument.activeElement) {
          (iframe.contentDocument.activeElement as HTMLElement).blur();
        }
        iframe.contentWindow.focus();
        iframe.contentWindow.print();
      }
    });
  }
});
