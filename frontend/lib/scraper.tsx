export async function getJobDescription(): Promise<string> {
    const [tab] = await browser.tabs.query({
        active: true,
        currentWindow: true
    })

    if (!tab || tab.id === undefined || !tab.url || tab.url.startsWith('chrome://')) {
        throw new Error("Invalid tab. Make sure you are on an active, non-chrome page.")
    }

    const results = await browser.scripting.executeScript({
        target: { tabId: tab.id },
        func: findJobDescription
    });

    if (!results || results.length === 0) {
        throw new Error("No script execution results returned from the page.");
    }

    return results[0].result ?? '';
}

function findJobDescription() {
    function findSelectedText() {
        const selection = window.getSelection();
        return selection?.toString().trim() ?? '';
    }

    function findResumeText() {
        const selectors = [
            // Specific job board containers (LinkedIn, Indeed, Amazon, etc.)
            '.jobs-description',
            '.jobs-description-content',
            '.jobs-box__html-content',
            '#jobDescriptionText',
            '.jobsearch-JobComponent-description',
            '.job-description-section',
            '#job-detail-body',
            // Generic description selectors
            '.job-description',
            '.description',
            '#job-description',
            '#jobDescription',
            '#description',
            '[id*="job-description"]',
            '[class*="job-description"]',
            '[class*="jobDescription"]',
            '[id*="jobDescription"]',
            '[class*="job_description"]',
            // Core main content elements
            'main',
            'article',
            '#content'
        ];

        for (const selector of selectors) {
            const element = document.querySelector(selector);
            if (element) {
                return element.textContent?.trim() ?? '';
            }
        }

        return '';
    }

    let jobDescription = findSelectedText();
    if (jobDescription.length > 0) {
        return jobDescription;
    }

    jobDescription = findResumeText();
    if (jobDescription.length > 0) {
        return jobDescription;
    }

    return document.body.innerText;
}