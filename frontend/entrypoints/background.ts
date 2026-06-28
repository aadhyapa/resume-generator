export default defineBackground(() => {
  browser.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type === 'GENERATE_RESUME') {
      browser.storage.local.set({
        generationState: 'generating'
      });

      const response = fetch('http://localhost:8000/generate_resume', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ job_description: message.jobDescription }),
      }).then((result) => {
        if (result.ok) {
          result.json().then((data) => {
            browser.storage.local.set({
              generationState: {
                status: 'success',
                jobDescription: data.jobDescription,
                resumeData: data.resume,
                errorMsg: '',
              }
            });
          });
        } else {
          browser.storage.local.set({
            generationState: {
              status: 'error',
              jobDescription: message.jobDescription,
              resumeData: null,
              errorMsg: 'Failed to generate resume.',
            }
          });
        }
      });
    }
  });
});
