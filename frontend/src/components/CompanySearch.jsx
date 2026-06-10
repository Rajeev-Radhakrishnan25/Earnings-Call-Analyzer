import React, { useState, useRef, useEffect } from 'react';
import { Search, Download, Check, X, Building2, Loader2 } from 'lucide-react';
import { api } from '../api/client';

const SECTOR_COLORS = {
  Technology: { bg: 'bg-blue-50', text: 'text-blue-700', dot: 'bg-blue-500' },
  Finance: { bg: 'bg-orange-50', text: 'text-orange-700', dot: 'bg-orange-500' },
  Healthcare: { bg: 'bg-purple-50', text: 'text-purple-700', dot: 'bg-purple-500' },
  Energy: { bg: 'bg-amber-50', text: 'text-amber-700', dot: 'bg-amber-500' },
  Automotive: { bg: 'bg-red-50', text: 'text-red-700', dot: 'bg-red-500' },
  Retail: { bg: 'bg-emerald-50', text: 'text-emerald-700', dot: 'bg-emerald-500' },
};

function getSectorStyle(sector) {
  return SECTOR_COLORS[sector] || SECTOR_COLORS.Technology;
}

export default function CompanySearch({ selectedTickers, onToggle, companies, onCompanyIngested }) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [ingesting, setIngesting] = useState({});
  const wrapperRef = useRef(null);

  useEffect(() => {
    function handleClickOutside(e) {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  useEffect(() => {
    if (!query || query.length < 1) {
      setResults([]);
      setIsOpen(false);
      return;
    }

    const timeout = setTimeout(async () => {
      setLoading(true);
      try {
        const data = await api.searchCompanies(query);
        setResults(data);
        setIsOpen(true);
      } catch {
        const q = query.toLowerCase();
        const filtered = companies.filter(
          c => c.ticker.toLowerCase().includes(q) || c.name.toLowerCase().includes(q)
        );
        setResults(filtered.map(c => ({ ...c, cik_number: c.cik_number || '', already_loaded: true })));
        setIsOpen(true);
      }
      setLoading(false);
    }, 200);

    return () => clearTimeout(timeout);
  }, [query, companies]);

  const handleIngestCompany = async (company) => {
    const ticker = company.ticker;
    setIngesting(prev => ({ ...prev, [ticker]: { status: 'starting', message: 'Starting...' } }));

    try {
      await api.ingestCompany(ticker);
      setIngesting(prev => ({ ...prev, [ticker]: { status: 'in_progress', message: 'Searching EDGAR...' } }));

      // Poll for completion
      const pollInterval = setInterval(async () => {
        try {
          const status = await api.ingestStatus(ticker);
          setIngesting(prev => ({ ...prev, [ticker]: status }));

          if (!status.in_progress) {
            clearInterval(pollInterval);
            if (status.status === 'completed') {
              // Refresh companies list
              if (onCompanyIngested) onCompanyIngested();
              onToggle(ticker);
            }
          }
        } catch {
          clearInterval(pollInterval);
        }
      }, 2000);
    } catch (err) {
      setIngesting(prev => ({
        ...prev,
        [ticker]: { status: 'failed', message: err.message, in_progress: false },
      }));
    }
  };

  const handleSelect = (company) => {
    if (company.already_loaded) {
      onToggle(company.ticker);
      setQuery('');
      setIsOpen(false);
    } else {
      handleIngestCompany(company);
    }
  };

  return (
    <div ref={wrapperRef} className="relative">
      <div className="flex items-center gap-2 px-3.5 py-2.5 border border-gray-200 rounded-xl bg-white focus-within:border-blue-400 transition-colors">
        <Building2 size={18} className="text-gray-400 shrink-0" />
        <div className="flex flex-wrap gap-1.5 flex-1 min-w-0">
          {selectedTickers.map(ticker => {
            const company = companies.find(c => c.ticker === ticker);
            const s = getSectorStyle(company?.sector);
            return (
              <span
                key={ticker}
                className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${s.bg} ${s.text}`}
              >
                {ticker}
                <X
                  size={12}
                  className="cursor-pointer opacity-60 hover:opacity-100"
                  onClick={() => onToggle(ticker)}
                />
              </span>
            );
          })}
          <input
            className="input-base flex-1 min-w-[120px]"
            placeholder={selectedTickers.length ? 'Add more...' : 'Search company or ticker to filter...'}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onFocus={() => query && setIsOpen(true)}
          />
        </div>
      </div>

      {isOpen && (
        <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-gray-200 rounded-xl shadow-lg z-20 max-h-72 overflow-y-auto">
          {loading && (
            <div className="px-4 py-3 text-sm text-gray-400 flex items-center gap-2">
              <Loader2 size={14} className="animate-spin" /> Searching...
            </div>
          )}
          {!loading && results.length === 0 && query && (
            <div className="px-4 py-3 text-sm text-gray-400">
              No companies found for "{query}"
            </div>
          )}
          {!loading && results.map((company) => {
            const s = getSectorStyle(company.sector);
            const isSelected = selectedTickers.includes(company.ticker);
            const ingestState = ingesting[company.ticker];
            const isIngesting = ingestState?.in_progress;

            return (
              <div
                key={company.ticker}
                className={`flex items-center justify-between px-4 py-2.5 border-b border-gray-100 last:border-0 transition-colors ${
                  isIngesting ? 'bg-blue-50/30' : 'cursor-pointer hover:bg-gradient-to-r hover:from-orange-50/50 hover:to-blue-50/50'
                }`}
                onClick={() => !isIngesting && handleSelect(company)}
              >
                <div className="flex items-center gap-3">
                  {isSelected && <Check size={14} className="text-blue-500" />}
                  {isIngesting && <Loader2 size={14} className="text-blue-500 animate-spin" />}
                  <span className="text-sm font-medium text-gray-900 w-12">{company.ticker}</span>
                  <span className="text-sm text-gray-500">{company.name}</span>
                </div>
                <div className="flex items-center gap-2">
                  {company.sector && (
                    <span className={`text-xs px-2 py-0.5 rounded-full ${s.bg} ${s.text}`}>
                      {company.sector}
                    </span>
                  )}
                  {isIngesting ? (
                    <span className="text-xs text-blue-500">{ingestState.message}</span>
                  ) : ingestState?.status === 'completed' ? (
                    <span className="text-xs text-green-600">Loaded</span>
                  ) : ingestState?.status === 'no_data' ? (
                    <span className="text-xs text-amber-600">EDGAR integration in progress</span>
                  ) : ingestState?.status === 'failed' ? (
                    <span className="text-xs text-red-500">Failed</span>
                  ) : company.already_loaded ? (
                    <span className="text-xs text-gray-400">loaded</span>
                  ) : (
                    <span className="text-xs text-blue-500 flex items-center gap-1">
                      <Download size={12} /> Load from EDGAR (beta)
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
