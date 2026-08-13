import { useEffect, useState } from "react";
import "./App.css";
import { Button } from "../../components/button";
import { getJobDescription } from "../../lib/scraper";
import { ResumePreview } from "./components/ResumePreview";
import type { GenerationState, GenerationStatus, Resume } from "./types";
import { isResume } from "./utils/resume";
import { renderResumeHtml } from "./utils/renderResumeHtml";
import { renderResumeLatex } from "./utils/renderResumeLatex";

function App() {
  const [jobDescription, setJobDescription] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [roleName, setRoleName] = useState("");
  const [status, setStatus] = useState<GenerationStatus>("idle");
  const [errorMsg, setErrorMsg] = useState("");
  const [resumeData, setResumeData] = useState<Resume | null>(null);
  const [authToken, setAuthToken] = useState("");
  const [showToken, setShowToken] = useState(false);

  function updateState(locallyStoredState: unknown) {
    if (!locallyStoredState) return;
    if (typeof locallyStoredState === "object") {
      const state = locallyStoredState as GenerationState;
      if (state.jobDescription !== undefined)
        setJobDescription(state.jobDescription);
      if (state.companyName !== undefined) setCompanyName(state.companyName);
      if (state.roleName !== undefined) setRoleName(state.roleName);
      if (state.status !== undefined) setStatus(state.status);
      if (state.resumeData !== undefined) {
        const nextResume = isResume(state.resumeData) ? state.resumeData : null;
        setResumeData(nextResume);
        if (!nextResume && state.status === "success") setStatus("idle");
      }
      if (state.errorMsg !== undefined) setErrorMsg(state.errorMsg);
    }
  }

  const handleAuthTokenChange = (val: string) => {
    setAuthToken(val);
    browser.storage.local.set({ authToken: val });
  };

  // Mounting hooks
  useEffect(() => {
    browser.storage.local.get(["generationState", "authToken"]).then((result: any) => {
      if (result) {
        if (result.generationState) {
          updateState(result.generationState);
        }
        if (result.authToken) {
          setAuthToken(result.authToken);
        }
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
    setCompanyName("");
    setRoleName("");
    setErrorMsg("");
    setStatus("idle");
    browser.storage.local.set({
      generationState: {
        status: "idle",
        jobDescription: "",
        companyName: "",
        roleName: "",
        resumeData: null,
        errorMsg: "",
      },
    });
  };

  const handleOpenHtmlPreview = async () => {
    if (!resumeData) return;

    const html = renderResumeHtml(resumeData);
    await browser.storage.local.set({ currentResumeHtml: html, currentResumeLatex: renderResumeLatex(resumeData) });
    const url = browser.runtime.getURL("/resume-preview.html");
    await browser.windows.create({
      url,
      type: "popup",
      width: 1000,
      height: 900,
    });
  };


  const getPdfFilename = () => {
    const fallbackCompany = companyName.trim() || "company";
    const fallbackRole = roleName.trim() || "jobtitle";
    const sanitize = (value: string) =>
      value
        .trim()
        .replace(/[^a-z0-9]+/gi, "_")
        .replace(/^_+|_+$/g, "")
        .toLowerCase() || "resume";
    return `${sanitize(fallbackCompany)}_${sanitize(fallbackRole)}.pdf`;
  };

  const handleDownloadPdf = async () => {
    if (!resumeData) return;
    setErrorMsg("");
    try {
      const latex = renderResumeLatex(resumeData);
      await browser.storage.local.set({ currentResumeLatex: latex });
      const apiBase = import.meta.env.WXT_API_URL ||
        "https://resume-generator-jtv0.onrender.com/generate_resume";
      const pdfUrl = apiBase.replace(/\/generate_resume\/?$/, "/render_resume_pdf");
      const headers: Record<string, string> = {
        "Content-Type": "application/json",
      };
      if (authToken) headers["X-API-Key"] = authToken;

      const response = await fetch(pdfUrl, {
        method: "POST",
        headers,
        body: JSON.stringify({ resume: resumeData }),
      });
      if (!response.ok) throw new Error("Failed to render LaTeX PDF.");

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = getPdfFilename();
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err: any) {
      console.error(err);
      const message = err.message || "An unknown error occurred while downloading the PDF.";
      setErrorMsg(message);
      window.alert(message);
    }
  };

  const handleGenerate = async () => {
    if (!jobDescription.trim()) return;
    browser.runtime
      .sendMessage({
        type: "GENERATE_RESUME",
        jobDescription,
        companyName,
        roleName,
        authToken,
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
        {/* API Key / Auth Token Input */}
        <div className="bg-black/25 border border-white/10 rounded-xl p-3 space-y-2">
          <div className="flex justify-between items-center text-[11px] text-white/80 px-1 font-semibold">
            <span className="flex items-center gap-1">
              <svg className="w-3.5 h-3.5 text-pink-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
              </svg>
              Auth Token
            </span>
          </div>
          <div className="relative flex items-center">
            <input
              type={showToken ? "text" : "password"}
              value={authToken}
              onChange={(e) => handleAuthTokenChange(e.target.value)}
              placeholder="Enter your auth token..."
              className="w-full bg-black/20 text-white placeholder-white/40 border border-white/20 rounded-lg py-1.5 pl-3 pr-8 text-xs focus:outline-none focus:ring-1 focus:ring-pink-300 focus:border-transparent transition-all duration-300 font-mono"
            />
            <button
              type="button"
              onClick={() => setShowToken(!showToken)}
              className="absolute right-2 text-white/50 hover:text-white transition-colors cursor-pointer"
            >
              {showToken ? (
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                </svg>
              ) : (
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                </svg>
              )}
            </button>
          </div>
        </div>

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
              <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                <input
                  type="text"
                  value={companyName}
                  onChange={(e) => setCompanyName(e.target.value)}
                  placeholder="Company name"
                  disabled={status === "generating"}
                  className="w-full bg-black/30 text-white/95 placeholder-white/50 border border-white/25 rounded-xl p-2.5 text-xs focus:outline-none focus:ring-2 focus:ring-pink-300 focus:border-transparent transition-all duration-300"
                />
                <input
                  type="text"
                  value={roleName}
                  onChange={(e) => setRoleName(e.target.value)}
                  placeholder="Role name"
                  disabled={status === "generating"}
                  className="w-full bg-black/30 text-white/95 placeholder-white/50 border border-white/25 rounded-xl p-2.5 text-xs focus:outline-none focus:ring-2 focus:ring-pink-300 focus:border-transparent transition-all duration-300"
                />
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
                onClick={handleDownloadPdf}
                className="preview-button"
              >
                Download PDF
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

            <div className="flex justify-center pt-1">
              <Button
                type="button"
                onClick={handleClear}
                className="exit-button"
              >
                Exit
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
