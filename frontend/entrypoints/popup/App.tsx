import { useState } from 'react';
import './App.css';
import { Button } from '../../components/button';
import { getJobDescription } from '../../lib/scraper';

interface Bullet {
  bullet_id: string;
  experience_id: string;
  text: string;
  bold_words?: string[];
}

type ResumeResponse = Record<string, Bullet[]> | Bullet[];

function App() {
  const [jobDescription, setJobDescription] = useState('');
  const [status, setStatus] = useState<'idle' | 'scraping' | 'scraped' | 'generating' | 'success' | 'error'>('idle');
  const [errorMsg, setErrorMsg] = useState('');
  const [resumeData, setResumeData] = useState<ResumeResponse | null>(null);

  function updateState(locallyStoredState: unknown) {
    if (!locallyStoredState) return;
    if (typeof locallyStoredState === 'object') {
      const state = locallyStoredState as {
        jobDescription?: string;
        status?: 'idle' | 'scraping' | 'scraped' | 'generating' | 'success' | 'error';
        resumeData?: ResumeResponse | null;
        errorMsg?: string;
      };
      if (state.jobDescription !== undefined) setJobDescription(state.jobDescription);
      if (state.status !== undefined) setStatus(state.status);
      if (state.resumeData !== undefined) setResumeData(state.resumeData);
      if (state.errorMsg !== undefined) setErrorMsg(state.errorMsg);
    }
  }

  // Mounting hooks
  useEffect(() => {
    browser.storage.local.get('generationState').then((result: any) => {
      if (result && result.generationState) {
        updateState(result.generationState);
      }
    });
    const listener = (changes: Record<string, Browser.storage.StorageChange>, area: string) => {
      if (area === 'local' && changes.generationState) {
        updateState(changes.generationState.newValue);
      }
    };
    browser.storage.onChanged.addListener(listener);
    return () => browser.storage.onChanged.removeListener(listener);
  }, []);

  // Scraping page
  const handleScrape = async () => {
    setStatus('scraping');
    setErrorMsg('');
    setResumeData(null);
    try {
      const scraped = await getJobDescription();
      if (scraped) {
        setJobDescription(scraped);
        setStatus('scraped');
      } else {
        setErrorMsg('Failed to extract job description from the page.');
        setStatus('error');
      }
    } catch (err: any) {
      console.error(err);
      setErrorMsg(err.message || 'An unknown error occurred while scraping.');
      setStatus('error');
    }
  };

  const handleGenerate = async () => {
    if (!jobDescription.trim()) return;
    browser.runtime.sendMessage({
      type: 'GENERATE_RESUME',
      jobDescription
    }).catch(err => {
      console.error(err);
      setErrorMsg(err.message || 'An unknown error occurred while generating resume.');
      setStatus('error');
    });
  };

  const renderBullets = () => {
    if (!resumeData) return null;

    // Helper to bold specific words in a text
    const highlightText = (text: string, boldWords?: string[]) => {
      // TODO (LEARN): Create a helper function that returns React elements (or styled text)
      // highlighting any word that matches one of the values inside boldWords.
      // 1. Return raw text if boldWords is empty or missing.
      // 2. Create a case-insensitive regex pattern matching any of the boldWords as word bounds (\b).
      // 3. Split the text using that regex pattern.
      // 4. Map over the split parts. If a part matches one of the boldWords, wrap it inside a styled <strong className="text-yellow-250 font-bold"> tag. Otherwise, return the plain text part.
      return text;
    };

    if (Array.isArray(resumeData)) {
      return (
        <ul className="space-y-3 text-left">
          {resumeData.map((bullet) => (
            <li key={bullet.bullet_id} className="bg-white/10 p-3 rounded-lg border border-white/10 backdrop-blur-sm text-sm transition-all duration-300 hover:bg-white/15">
              <span className="text-xs text-pink-200 uppercase font-semibold block mb-1">
                {bullet.experience_id}
              </span>
              <p className="text-white/90">
                {highlightText(bullet.text, bullet.bold_words)}
              </p>
            </li>
          ))}
        </ul>
      );
    }

    return (
      <div className="space-y-6 text-left">
        {Object.entries(resumeData).map(([experienceId, bullets]) => (
          <div key={experienceId} className="bg-black/25 p-4 rounded-xl border border-white/10 backdrop-blur-md">
            <h3 className="text-pink-300 font-semibold text-xs uppercase tracking-wider mb-2 border-b border-pink-500/20 pb-1">
              Experience: {experienceId}
            </h3>
            <ul className="space-y-2">
              {bullets.map((bullet) => (
                <li key={bullet.bullet_id} className="text-xs text-white/95 leading-relaxed relative pl-3 before:content-['•'] before:absolute before:left-0 before:text-pink-400">
                  {highlightText(bullet.text, bullet.bold_words)}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    );
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
            disabled={status === 'scraping' || status === 'generating'}
            className="tailor-button"
          >
            {status === 'scraping' ? (
              <>
                <svg className="animate-spin h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                Scraping...
              </>
            ) : (
              'Tailor'
            )}
          </Button>
        </div>

        {/* Error State */}
        {status === 'error' && (
          <div className="bg-red-500/20 border border-red-500/30 p-3 rounded-xl text-xs text-red-200 text-left">
            <span className="font-bold">Error:</span> {errorMsg}
          </div>
        )}

        {/* Text Area for Edit / Preview */}
        {(status === 'scraped' || status === 'generating' || status === 'success' || status === 'error' || jobDescription) && (
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
              disabled={status === 'generating'}
              className="w-full h-32 bg-black/30 text-white/95 placeholder-white/50 border border-white/25 rounded-xl p-3 text-xs focus:outline-none focus:ring-2 focus:ring-pink-300 focus:border-transparent transition-all duration-300 resize-none font-sans leading-relaxed scrollbar-thin scrollbar-thumb-white/20"
            />

            {/* Generate Action */}
            <div className="flex justify-center">
              <Button
                onClick={handleGenerate}
                disabled={status === 'generating' || !jobDescription.trim()}
                className="flex justify-center"
              >
                {status === 'generating' ? (
                  <>
                    <svg className="animate-spin h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    Tailoring Resume...
                  </>
                ) : (
                  'Generate Tailored Resume'
                )}
              </Button>
            </div>
          </div>
        )}

        {/* Success / Tailored Resume Section */}
        {status === 'success' && resumeData && (
          <div className="space-y-3 pt-1">
            <div className="flex items-center gap-2 bg-emerald-500/20 border border-emerald-500/30 p-3 rounded-xl text-xs text-emerald-250">
              <span>Resume Tailoring complete! Tailored bullets:</span>
            </div>

            <div className="max-h-60 overflow-y-auto pr-1 space-y-3 scrollbar-thin scrollbar-thumb-white/20">
              {renderBullets()}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
