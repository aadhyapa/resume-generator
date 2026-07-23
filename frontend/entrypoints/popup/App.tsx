import { useEffect, useState } from "react";
import "./App.css";
import { Button } from "../../components/button";
import { getJobDescription } from "../../lib/scraper";
import { ResumePreview } from "./components/ResumePreview";
import type { GenerationState, GenerationStatus, Resume } from "./types";
import { isResume } from "./utils/resume";
import { renderResumeHtml } from "./utils/renderResumeHtml";

function App() {
  const [jobDescription, setJobDescription] = useState("");
  const [status, setStatus] = useState<GenerationStatus>("idle");
  const [errorMsg, setErrorMsg] = useState("");
  const [resumeData, setResumeData] = useState<Resume | null>(null);

  function updateState(locallyStoredState: unknown) {
    if (!locallyStoredState) return;
    if (typeof locallyStoredState === "object") {
      const state = locallyStoredState as GenerationState;
      if (state.jobDescription !== undefined)
        setJobDescription(state.jobDescription);
      if (state.status !== undefined) setStatus(state.status);
      if (state.resumeData !== undefined) {
        const nextResume = isResume(state.resumeData) ? state.resumeData : null;
        setResumeData(nextResume);
        if (!nextResume && state.status === "success") setStatus("idle");
      }
      if (state.errorMsg !== undefined) setErrorMsg(state.errorMsg);
    }
  }

  // Mounting hooks
  useEffect(() => {
    browser.storage.local.get("generationState").then((result: any) => {
      if (result && result.generationState) {
        updateState(result.generationState);
      }
    });
    const listener = (
      changes: Record<string, Browser.storage.StorageChange>,
      area: string,
    ) => {
      if (area === "local" && changes.generationState) {
        updateState(changes.generationState.newValue);
      }
    };
    browser.storage.onChanged.addListener(listener);
    return () => browser.storage.onChanged.removeListener(listener);
  }, []);

  // Scraping page
  const handleScrape = async () => {
    setStatus("scraping");
    setErrorMsg("");
    setResumeData(null);
    try {
      const scraped = await getJobDescription();
      if (scraped) {
        setJobDescription(scraped);
        setStatus("scraped");
      } else {
        setErrorMsg("Failed to extract job description from the page.");
        setStatus("error");
      }
    } catch (err: any) {
      console.error(err);
      setErrorMsg(err.message || "An unknown error occurred while scraping.");
      setStatus("error");
    }
  };

  const handleClear = () => {
    setJobDescription("");
    setResumeData(null);
    setErrorMsg("");
    setStatus("idle");
    browser.storage.local.set({
      generationState: {
        status: "idle",
        jobDescription: "",
        resumeData: null,
        errorMsg: "",
      },
    });
  };

  const handleOpenHtmlPreview = async () => {
    if (!resumeData) return;

    const html = renderResumeHtml(resumeData);
    await browser.storage.local.set({ currentResumeHtml: html });
    const url = browser.runtime.getURL("/resume-preview.html");
    await browser.windows.create({
      url,
      type: "popup",
      width: 1000,
      height: 900,
    });
  };

  const handleGenerate = async () => {
    if (!jobDescription.trim()) return;
    browser.runtime
      .sendMessage({
        type: "GENERATE_RESUME",
        jobDescription,
      })
      .catch((err) => {
        console.error(err);
        setErrorMsg(
          err.message || "An unknown error occurred while generating resume.",
        );
        setStatus("error");
      });
  };

  return (
    <div className="w-full p-5 text-white select-none">
      <div className="flex flex-col items-center mb-5">
        <h1 className="text-6xl tracking-tight drop-shadow-md select-none text-white leading-none mb-2">
          Rezmaker
        </h1>
        <p className="text-xs text-white/80 select-none font-medium tracking-wide">
          Resume Personalization Agent
        </p>
      </div>

      <div className="space-y-4">
        {/* Main Action Buttons */}
        <div className="flex justify-center">
          <Button
            onClick={handleScrape}
            disabled={status === "scraping" || status === "generating"}
            className="tailor-button"
          >
            {status === "scraping" ? (
              <>
                <svg
                  className="animate-spin h-4 w-4 text-white"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  />
                </svg>
                Scraping...
              </>
            ) : (
              "Scrape"
            )}
          </Button>
        </div>

        {/* Error State */}
        {status === "error" && (
          <div className="bg-red-500/20 border border-red-500/30 p-3 rounded-xl text-xs text-red-200 text-left">
            <span className="font-bold">Error:</span> {errorMsg}
          </div>
        )}

        {/* Text Area for Edit / Preview */}
        {(status === "scraped" ||
          status === "generating" ||
          status === "success" ||
          status === "error" ||
          jobDescription) && (
            <div className="space-y-3">
              <div className="flex justify-between items-center text-[11px] text-white/90 px-1 font-semibold">
                <span></span>
                <span className="text-[10px] bg-white/20 px-2 py-0.5 rounded-full font-normal">
                  {jobDescription.length} chars
                </span>
              </div>
              <textarea
                value={jobDescription}
                onChange={(e) => setJobDescription(e.target.value)}
                placeholder="Paste or edit the job description here..."
                disabled={status === "generating"}
                className="w-full h-32 bg-black/30 text-white/95 placeholder-white/50 border border-white/25 rounded-xl p-3 text-xs focus:outline-none focus:ring-2 focus:ring-pink-300 focus:border-transparent transition-all duration-300 resize-none font-sans leading-relaxed scrollbar-thin scrollbar-thumb-white/20"
              />

              {/* Clear / Generate Actions */}
              <div className="resume-actions">
                <Button
                  type="button"
                  onClick={handleClear}
                  disabled={status === "generating" || !jobDescription}
                  aria-label="Clear job description"
                  className="clear-button"
                >
                  Clear
                </Button>
                <Button
                  onClick={handleGenerate}
                  disabled={status === "generating" || !jobDescription.trim()}
                  className="flex justify-center"
                >
                  {status === "generating" ? (
                    <>
                      <svg
                        className="animate-spin h-4 w-4 text-white"
                        fill="none"
                        viewBox="0 0 24 24"
                      >
                        <circle
                          className="opacity-25"
                          cx="12"
                          cy="12"
                          r="10"
                          stroke="currentColor"
                          strokeWidth="4"
                        />
                        <path
                          className="opacity-75"
                          fill="currentColor"
                          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                        />
                      </svg>
                      Tailoring Resume...
                    </>
                  ) : (
                    "Tailor"
                  )}
                </Button>
              </div>
            </div>
          )}

        {/* Success / Tailored Resume Section */}
        {status === "success" && resumeData && (
          <div className="space-y-3 pt-1">
            <div className="flex items-center gap-2 bg-emerald-500/20 border border-emerald-500/30 p-3 rounded-xl text-xs text-emerald-250">
              <span>
                Resume tailoring complete! Review your tailored resume below.
              </span>
            </div>

            <div className="resume-actions">
              <Button
                type="button"
                onClick={handleOpenHtmlPreview}
                className="preview-button"
              >
                Preview
              </Button>
              <Button
                type="button"
                onClick={handleClear}
                className="exit-button"
              >
                Exit
              </Button>
            </div>

            <div className="max-h-60 overflow-y-auto pr-1 space-y-3 scrollbar-thin scrollbar-thumb-white/20">
              <ResumePreview resume={resumeData} />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
