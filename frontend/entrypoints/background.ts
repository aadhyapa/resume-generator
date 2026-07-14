import type { GenerateResumeResponse } from './popup/types';
import { isResume } from './popup/utils/resume';

export default defineBackground(() => {
  browser.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type === 'GENERATE_RESUME') {
      browser.storage.local.set({
        generationState: {
          status: 'generating',
          jobDescription: message.jobDescription,
          resumeData: null,
          errorMsg: '',
        }
      });

      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 180000); // 3 minutes timeout

      fetch('http://localhost:8000/generate_resume', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ job_description: message.jobDescription }),
        signal: controller.signal,
      })
        .then((result) => {
          clearTimeout(timeoutId);
          if (result.ok) {
            return result.json();
          } else {
            throw new Error('Failed to generate resume.');
          }
        })
        .then((data: GenerateResumeResponse) => {
          if (!isResume(data.resume)) {
            throw new Error('Backend response did not include a valid resume.');
          }

          browser.storage.local.set({
            generationState: {
              status: 'success',
              jobDescription: message.jobDescription,
              resumeData: data.resume,
              errorMsg: '',
            }
          });
        })
        .catch((err) => {
          clearTimeout(timeoutId);
          const isTimeout = err.name === 'AbortError';
          browser.storage.local.set({
            generationState: {
              status: 'error',
              jobDescription: message.jobDescription,
              resumeData: null,
              errorMsg: isTimeout
                ? 'Generation timed out. The server took too long to respond.'
                : (err.message || 'Failed to generate resume.'),
            }
          });
        });
    }
  });
});
