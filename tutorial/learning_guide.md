# Learning Guide: Building a Page-Scraping Chrome Extension with a Backend

This guide outlines step-by-step how to build a modern Chrome extension (using WXT & React) that scrapes text from the active webpage and integrates with a FastAPI backend.

---

## Step 1: Initialize the Chrome Extension Framework

To avoid writing low-level boilerplates, use **WXT** (Next-gen Web Extension Framework) which comes pre-configured with bundlers like Vite.

1. **Create the Project**:
   ```bash
   npx wxt@latest init resume-generator-extension
   ```
   *Choose React and Tailwind CSS templates when prompted.*

2. **Understand WXT Structure**:
   - `entrypoints/popup/index.html` & `App.tsx`: The HTML/JS rendered when clicking the extension icon.
   - `wxt.config.ts`: The main configuration file that compiles into `manifest.json`.

---

## Step 2: Request Chrome Permissions

To scrape pages, Chrome requires permissions. Add them to your `wxt.config.ts` so they compile into `manifest.json`.

```typescript
// wxt.config.ts
export default defineConfig({
  manifest: {
    permissions: ['activeTab', 'scripting'],
  }
});
```

* **`activeTab`**: Grants temporary, secure permission to inspect the active browser tab when the user interacts with the extension.
* **`scripting`**: Allows the extension to programmatically run JavaScript functions inside that active tab.

---

## Step 3: Implement Web Scraping in React

Inside `App.tsx`, build a function to execute a scraper script inside the context of the active tab.

```typescript
const handleScrape = async () => {
  // 1. Get the current active tab
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab || !tab.id) return;

  // 2. Inject script into the active tab
  const results = await chrome.scripting.executeScript({
    target: { tabId: tab.id },
    func: () => {
      // Runs directly in the browser page context:
      
      // Target user highlighted text first (precision)
      const selection = window.getSelection()?.toString();
      if (selection?.trim()) return selection.trim();

      // Check common job selectors
      const selectors = ['.job-description', '#content', 'main'];
      for (const selector of selectors) {
        const el = document.querySelector(selector);
        if (el?.innerText) return el.innerText;
      }

      // Fallback to entire page text
      return document.body.innerText;
    }
  });

  const scrapedText = results?.[0]?.result;
  console.log("Scraped text: ", scrapedText);
};
```

---

## Step 4: Configure Backend CORS

Because your Chrome extension runs on a special origin (`chrome-extension://<id>`), browser safety rules will block requests to your local backend (`localhost`) unless CORS is enabled.

In your FastAPI backend application, configure the CORS middleware:

```python
# app.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this to your extension's origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Step 5: Connect Extension to the Backend

In `App.tsx`, create a trigger function that sends the scraped text to your local API:

```typescript
const handleGenerate = async (text: string) => {
  const response = await fetch('http://localhost:8000/generate_resume', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ job_description: text }),
  });

  const data = await response.json();
  console.log("Tailored resume bullets: ", data.resume);
};
```

---

## Step 6: Design & Style the Extension

A great extension feels compact, readable, and premium.
1. Define a fixed width on your root container (e.g. `w-[360px]`) so Chrome sets the popup width correctly.
2. Use modern colors, rounded cards, and visual states (`loading`, `success`, `error`) to guide the user.
3. Allow users to review and edit the scraped description before submitting to prevent LLM mistakes.
