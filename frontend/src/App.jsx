import React, { useState, useEffect, useCallback } from 'react';
import {
  Search, Mic, MicOff, ArrowRight, Calendar, List, User,
  ArrowLeftRight, SmilePlus, Database, TrendingUp,
  Loader2,
} from 'lucide-react';
import Logo from './components/Logo';
import CompanySearch from './components/CompanySearch';
import ResultsPanel from './components/ResultsPanel';
import SentimentChart from './components/SentimentChart';
import { useVoiceInput } from './hooks/useVoiceInput';
import { api } from './api/client';

const SAMPLE_QUERIES = [
  "How has Apple's services revenue narrative evolved over the past year?",
  "What did Microsoft's CFO say about AI capital expenditure?",
  "Compare NVIDIA and Oracle's cloud growth strategies",
  "How has JPMorgan's credit quality outlook changed across quarters?",
];

const FILTER_OPTIONS = {
  quarters: ['Q1', 'Q2', 'Q3', 'Q4'],
  sections: ['prepared_remarks', 'qa'],
  roles: ['ceo', 'cfo', 'analyst', 'executive'],
};

export default function App() {
  const [queryText, setQueryText] = useState('');
  const [selectedTickers, setSelectedTickers] = useState([]);
  const [companies, setCompanies] = useState([]);
  const [stats, setStats] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activeFilters, setActiveFilters] = useState({ quarters: [], section: null, roles: [] });
  const [enableTemporal, setEnableTemporal] = useState(false);
  const [enableSentiment, setEnableSentiment] = useState(false);
  const [sentimentData, setSentimentData] = useState(null);
  const [sentimentLoading, setSentimentLoading] = useState(false);
  const [seedingStatus, setSeedingStatus] = useState(null);

  const handleVoiceResult = useCallback((text) => setQueryText(text), []);
  const { isListening, toggle: toggleVoice, isSupported: voiceSupported, interim } = useVoiceInput(handleVoiceResult);

  const refreshData = useCallback(async () => {
    try {
      const [c, s] = await Promise.all([
        api.listCompanies().catch(() => []),
        api.getStats().catch(() => null),
      ]);
      setCompanies(c);
      setStats(s);
    } catch {}
  }, []);

  useEffect(() => {
    let interval;
    async function checkSeeding() {
      try {
        const status = await api.seedingStatus();
        setSeedingStatus(status);
        if (status.in_progress) {
          interval = setInterval(async () => {
            try {
              const updated = await api.seedingStatus();
              setSeedingStatus(updated);
              if (!updated.in_progress) { clearInterval(interval); refreshData(); }
            } catch { clearInterval(interval); }
          }, 3000);
        } else { refreshData(); }
      } catch { setTimeout(checkSeeding, 2000); }
    }
    checkSeeding();
    return () => interval && clearInterval(interval);
  }, [refreshData]);

  const toggleTicker = useCallback((t) => {
    setSelectedTickers(prev => prev.includes(t) ? prev.filter(x => x !== t) : [...prev, t]);
  }, []);

  const toggleFilter = useCallback((type, value) => {
    setActiveFilters(prev => {
      if (type === 'section') return { ...prev, section: prev.section === value ? null : value };
      const list = prev[type] || [];
      return { ...prev, [type]: list.includes(value) ? list.filter(v => v !== value) : [...list, value] };
    });
  }, []);

  const handleSubmit = useCallback(async () => {
    if (!queryText.trim()) return;
    setLoading(true); setError(null); setResult(null); setSentimentData(null);
    try {
      const data = await api.query({
        question: queryText,
        company_tickers: selectedTickers.length > 0 ? selectedTickers : null,
        quarters: activeFilters.quarters.length > 0 ? activeFilters.quarters : null,
        section_type: activeFilters.section || null,
        speaker_roles: activeFilters.roles.length > 0 ? activeFilters.roles : null,
        enable_temporal_comparison: enableTemporal,
        enable_sentiment: enableSentiment,
        top_k: 10,
      });
      setResult(data);
      if (enableSentiment && selectedTickers.length === 1) {
        setSentimentLoading(true);
        try { const s = await api.sentiment(selectedTickers[0]); setSentimentData(s); } catch {}
        setSentimentLoading(false);
      }
    } catch (err) { setError(err.message || 'Query failed.'); }
    setLoading(false);
  }, [queryText, selectedTickers, activeFilters, enableTemporal, enableSentiment]);

  const handleKeyDown = (e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSubmit(); } };

  const resetToHome = useCallback(() => {
    setQueryText(''); setSelectedTickers([]); setResult(null); setError(null);
    setSentimentData(null); setEnableTemporal(false); setEnableSentiment(false);
    setActiveFilters({ quarters: [], section: null, roles: [] });
  }, []);

  const isSeeding = seedingStatus?.in_progress;

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-4xl mx-auto px-4 py-3 flex items-center justify-between">
          <button onClick={resetToHome} className="flex items-center gap-2.5 hover:opacity-80 transition-opacity">
            <Logo size={34} />
            <span className="font-medium text-gray-900">Earnings Call Analyzer</span>
          </button>
          <nav className="flex items-center gap-5">
            <button onClick={resetToHome} className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-blue-500 transition-colors">
              <Database size={15} /> Companies
            </button>
            <button onClick={() => { resetToHome(); setEnableTemporal(true); setQueryText("How has AI strategy evolved over the past year?"); }} className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-blue-500 transition-colors">
              <TrendingUp size={15} /> Trends
            </button>
            <button onClick={() => { resetToHome(); setEnableSentiment(true); setQueryText("What is the overall outlook and guidance?"); }} className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-blue-500 transition-colors">
              <SmilePlus size={15} /> Sentiment
            </button>
          </nav>
        </div>
        <div className="gradient-line" />
      </header>

      <main className="max-w-2xl mx-auto px-4 pt-8 pb-16">
        {isSeeding && (
          <div className="mb-8 p-6 bg-white border border-blue-200 rounded-xl text-center">
            <Loader2 size={32} className="animate-spin text-blue-500 mx-auto mb-3" />
            <h2 className="text-lg font-medium text-gray-900 mb-1">Setting up for first time</h2>
            <p className="text-sm text-gray-500 mb-3">Loading transcripts and generating embeddings. This takes a few minutes on first run.</p>
            <div className="w-full bg-gray-200 rounded-full h-2 mb-2">
              <div className="h-2 rounded-full transition-all duration-500" style={{
                width: seedingStatus.total > 0 ? `${(seedingStatus.progress / seedingStatus.total) * 100}%` : '10%',
                background: 'linear-gradient(90deg, #F97316, #3B82F6)',
              }} />
            </div>
            <p className="text-xs text-gray-400">{seedingStatus.message}</p>
          </div>
        )}

        <div className="text-center mb-8">
          <h1 className="text-2xl font-medium text-gray-900 mb-2">Analyze earnings calls with AI</h1>
          <p className="text-sm text-gray-500">Natural language queries across SEC EDGAR transcripts. Cited answers in seconds.</p>
        </div>

        <div className="mb-3">
          <CompanySearch selectedTickers={selectedTickers} onToggle={toggleTicker} companies={companies} onCompanyIngested={refreshData} />
        </div>

        <div className="flex items-center gap-2 px-3.5 py-2.5 border border-gray-200 rounded-xl bg-white focus-within:border-blue-400 transition-colors mb-3">
          <Search size={18} className="text-gray-400 shrink-0" />
          <input className="input-base flex-1" placeholder={isListening && interim ? interim : "Ask about earnings, guidance, revenue, strategy..."} value={queryText} onChange={(e) => setQueryText(e.target.value)} onKeyDown={handleKeyDown} disabled={isSeeding} />
          {voiceSupported && (
            <button onClick={toggleVoice} disabled={isSeeding} className={`w-8 h-8 rounded-full flex items-center justify-center transition-all shrink-0 ${isListening ? 'bg-red-50 text-red-500 border border-red-200' : 'bg-gray-50 text-gray-400 border border-gray-200 hover:text-gray-600'}`} title="Voice input">
              {isListening ? <MicOff size={15} /> : <Mic size={15} />}
            </button>
          )}
          <button onClick={handleSubmit} disabled={loading || !queryText.trim() || isSeeding} className="btn-primary flex items-center gap-1.5 shrink-0 disabled:opacity-50">
            {loading ? <Loader2 size={15} className="animate-spin" /> : <ArrowRight size={15} />} Ask
          </button>
        </div>

        <div className="flex gap-2 mb-6 flex-wrap">
          <div className="relative group">
            <button className={`text-xs px-3 py-1.5 rounded-full border flex items-center gap-1.5 transition-all ${activeFilters.quarters.length > 0 ? 'border-blue-300 text-blue-600 bg-blue-50' : 'border-gray-200 text-gray-500 bg-white hover:border-gray-300'}`}>
              <Calendar size={13} /> {activeFilters.quarters.length > 0 ? activeFilters.quarters.join(', ') : 'All quarters'}
            </button>
            <div className="hidden group-hover:block absolute top-full left-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-10 p-2 min-w-[120px]">
              {FILTER_OPTIONS.quarters.map(q => (<button key={q} onClick={() => toggleFilter('quarters', q)} className={`block w-full text-left text-xs px-3 py-1.5 rounded hover:bg-gray-50 ${activeFilters.quarters.includes(q) ? 'text-blue-600 font-medium' : 'text-gray-600'}`}>{activeFilters.quarters.includes(q) ? '\u2713 ' : ''}{q}</button>))}
            </div>
          </div>
          <div className="relative group">
            <button className={`text-xs px-3 py-1.5 rounded-full border flex items-center gap-1.5 transition-all ${activeFilters.section ? 'border-blue-300 text-blue-600 bg-blue-50' : 'border-gray-200 text-gray-500 bg-white hover:border-gray-300'}`}>
              <List size={13} /> {activeFilters.section ? activeFilters.section.replace('_', ' ') : 'All sections'}
            </button>
            <div className="hidden group-hover:block absolute top-full left-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-10 p-2 min-w-[160px]">
              {FILTER_OPTIONS.sections.map(s => (<button key={s} onClick={() => toggleFilter('section', s)} className={`block w-full text-left text-xs px-3 py-1.5 rounded hover:bg-gray-50 capitalize ${activeFilters.section === s ? 'text-blue-600 font-medium' : 'text-gray-600'}`}>{activeFilters.section === s ? '\u2713 ' : ''}{s.replace('_', ' ')}</button>))}
            </div>
          </div>
          <div className="relative group">
            <button className={`text-xs px-3 py-1.5 rounded-full border flex items-center gap-1.5 transition-all ${activeFilters.roles.length > 0 ? 'border-blue-300 text-blue-600 bg-blue-50' : 'border-gray-200 text-gray-500 bg-white hover:border-gray-300'}`}>
              <User size={13} /> {activeFilters.roles.length > 0 ? activeFilters.roles.map(r => r.toUpperCase()).join(', ') : 'All speakers'}
            </button>
            <div className="hidden group-hover:block absolute top-full left-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-10 p-2 min-w-[120px]">
              {FILTER_OPTIONS.roles.map(r => (<button key={r} onClick={() => toggleFilter('roles', r)} className={`block w-full text-left text-xs px-3 py-1.5 rounded hover:bg-gray-50 uppercase ${activeFilters.roles.includes(r) ? 'text-blue-600 font-medium' : 'text-gray-600'}`}>{activeFilters.roles.includes(r) ? '\u2713 ' : ''}{r}</button>))}
            </div>
          </div>
          <button onClick={() => setEnableTemporal(!enableTemporal)} className={`text-xs px-3 py-1.5 rounded-full border flex items-center gap-1.5 transition-all ${enableTemporal ? 'border-blue-300 text-blue-600 bg-blue-50' : 'border-gray-200 text-gray-500 bg-white hover:border-gray-300'}`} style={enableTemporal ? {} : { borderLeftWidth: '2px', borderLeftColor: '#3B82F6' }}>
            <ArrowLeftRight size={13} /> Compare quarters
          </button>
          <button onClick={() => setEnableSentiment(!enableSentiment)} className={`text-xs px-3 py-1.5 rounded-full border flex items-center gap-1.5 transition-all ${enableSentiment ? 'border-orange-300 text-orange-600 bg-orange-50' : 'border-gray-200 text-gray-500 bg-white hover:border-gray-300'}`} style={enableSentiment ? {} : { borderLeftWidth: '2px', borderLeftColor: '#F97316' }}>
            <SmilePlus size={13} /> Sentiment analysis
          </button>
        </div>

        {!result && !loading && !isSeeding && (
          <>
            <div className="mb-6">
              <p className="text-xs text-gray-400 uppercase tracking-wider mb-2.5">Try asking</p>
              <div className="space-y-2">
                {SAMPLE_QUERIES.map((q, i) => (<button key={i} onClick={() => setQueryText(q)} className="block w-full text-left px-4 py-2.5 border border-gray-200 rounded-lg text-sm text-gray-500 hover:border-orange-300 hover:text-orange-600 hover:bg-orange-50/30 transition-all">{q}</button>))}
              </div>
            </div>
            {companies.length > 0 && (
              <div className="mb-6">
                <div className="flex items-center justify-between mb-2.5">
                  <p className="text-xs text-gray-400 uppercase tracking-wider">Loaded companies</p>
                  <button onClick={() => { const all = companies.map(c => c.ticker); setSelectedTickers(all.every(t => selectedTickers.includes(t)) ? [] : all); }} className="text-xs text-blue-500 hover:text-blue-600">
                    {companies.every(c => selectedTickers.includes(c.ticker)) ? 'Clear all' : 'Select all'}
                  </button>
                </div>
                <div className="flex gap-1.5 flex-wrap">
                  {companies.map(c => {
                    const on = selectedTickers.includes(c.ticker);
                    return (<button key={c.ticker} onClick={() => toggleTicker(c.ticker)} className={`text-xs px-2.5 py-1 rounded-full border transition-all flex items-center gap-1 ${on ? 'border-blue-300 bg-gradient-to-r from-orange-50/50 to-blue-50/50 text-blue-700 font-medium' : 'border-gray-200 text-gray-500 hover:border-gray-300'}`}>{on && <span className="text-blue-500">{'\u2713'}</span>}{c.ticker}</button>);
                  })}
                </div>
                <p className="text-xs text-gray-400 mt-2">Click to select. Additional companies and live EDGAR integration coming soon.</p>
              </div>
            )}
            {stats && (
              <div className="grid grid-cols-3 gap-3 mb-6">
                <div className="card-glow rounded-lg p-3.5 border border-gray-100"><p className="text-xs text-gray-400 mb-0.5">Transcripts</p><p className="text-xl font-medium text-gray-900">{stats.total_transcripts}</p></div>
                <div className="card-glow rounded-lg p-3.5 border border-gray-100"><p className="text-xs text-gray-400 mb-0.5">Companies</p><p className="text-xl font-medium text-gray-900">{stats.total_companies}</p>{stats.other_companies > 0 && <p className="text-xs text-gray-400">{stats.sp500_companies} S&P 500 + {stats.other_companies} other</p>}</div>
                <div className="card-glow rounded-lg p-3.5 border border-gray-100"><p className="text-xs text-gray-400 mb-0.5">Coverage</p><p className="text-xl font-medium text-gray-900">{stats.quarters_covered}Q</p>{stats.oldest_quarter && stats.newest_quarter && <p className="text-xs text-gray-400">{stats.oldest_quarter} to {stats.newest_quarter}</p>}</div>
              </div>
            )}
          </>
        )}

        <ResultsPanel result={result} loading={loading} error={error} />
        {sentimentData && <SentimentChart data={sentimentData.data_points} loading={sentimentLoading} company={sentimentData.company} analysis={sentimentData.analysis} trend={sentimentData.overall_trend} />}

        <div className="text-center mt-12 pt-4 border-t border-gray-100">
          <p className="text-xs text-gray-400">Powered by SEC EDGAR public filings, pgvector, and Claude Opus 4.6. Live EDGAR ingestion for additional companies is under active development.</p>
        </div>
      </main>
    </div>
  );
}
