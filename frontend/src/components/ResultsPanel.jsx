import React from 'react';
import { Clock, FileText, User, Building2, Quote } from 'lucide-react';

function CitationCard({ citation, index }) {
  const roleColors = {
    ceo: 'border-l-orange-400 bg-orange-50/30',
    cfo: 'border-l-blue-400 bg-blue-50/30',
    analyst: 'border-l-purple-400 bg-purple-50/30',
    executive: 'border-l-emerald-400 bg-emerald-50/30',
  };
  const colorClass = roleColors[citation.speaker_role] || 'border-l-gray-300 bg-gray-50/30';

  return (
    <div className={`border-l-4 rounded-r-lg p-3 ${colorClass} transition-all hover:shadow-sm`}>
      <div className="flex items-center gap-2 mb-1.5 flex-wrap">
        <span className="text-xs font-medium text-gray-900 bg-white px-2 py-0.5 rounded-full border border-gray-200">
          [{index}]
        </span>
        <span className="flex items-center gap-1 text-xs text-gray-600">
          <Building2 size={12} />
          {citation.ticker}
        </span>
        <span className="flex items-center gap-1 text-xs text-gray-600">
          <Clock size={12} />
          {citation.quarter} {citation.year}
        </span>
        <span className="flex items-center gap-1 text-xs text-gray-600">
          <User size={12} />
          {citation.speaker}
        </span>
        <span className="text-xs text-gray-400 capitalize">
          {citation.speaker_role}
        </span>
        <span className="text-xs text-gray-400 capitalize">
          {citation.section.replace('_', ' ')}
        </span>
      </div>
      <p className="text-sm text-gray-700 leading-relaxed">{citation.excerpt}</p>
      <div className="mt-1.5">
        <div className="h-1 w-full bg-gray-200 rounded-full overflow-hidden">
          <div
            className="h-full rounded-full"
            style={{
              width: `${Math.max(citation.relevance_score * 100, 10)}%`,
              background: 'linear-gradient(90deg, #F97316, #3B82F6)',
            }}
          />
        </div>
        <span className="text-xs text-gray-400 mt-0.5 inline-block">
          {(citation.relevance_score * 100).toFixed(0)}% relevance
        </span>
      </div>
    </div>
  );
}

export default function ResultsPanel({ result, loading, error }) {
  if (loading) {
    return (
      <div className="mt-6 space-y-3 animate-pulse">
        <div className="h-4 bg-gray-200 rounded w-3/4" />
        <div className="h-4 bg-gray-200 rounded w-full" />
        <div className="h-4 bg-gray-200 rounded w-5/6" />
        <div className="h-4 bg-gray-200 rounded w-2/3" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="mt-6 p-4 bg-red-50 border border-red-200 rounded-xl">
        <p className="text-sm text-red-700">{error}</p>
      </div>
    );
  }

  if (!result) return null;

  return (
    <div className="mt-6 space-y-4">
      {/* Answer */}
      <div className="bg-white border border-gray-200 rounded-xl p-5">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-medium text-gray-900">Answer</h3>
          <div className="flex items-center gap-3 text-xs text-gray-400">
            <span className="flex items-center gap-1">
              <Clock size={12} />
              {result.query_time_ms}ms
            </span>
            <span className="flex items-center gap-1">
              <FileText size={12} />
              {result.chunks_retrieved} sources
            </span>
          </div>
        </div>
        <div className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">
          {result.answer}
        </div>
        {result.companies_searched?.length > 0 && (
          <div className="mt-3 flex items-center gap-2">
            <span className="text-xs text-gray-400">Searched:</span>
            {result.companies_searched.map(t => (
              <span key={t} className="text-xs px-2 py-0.5 rounded-full bg-gray-100 text-gray-600">
                {t}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Citations */}
      {result.citations?.length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-gray-900 mb-3 flex items-center gap-2">
            <Quote size={14} />
            Sources ({result.citations.length})
          </h3>
          <div className="space-y-2">
            {result.citations.map((citation, i) => (
              <CitationCard key={i} citation={citation} index={i + 1} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
