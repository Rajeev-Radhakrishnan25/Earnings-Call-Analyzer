import React from 'react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
} from 'recharts';

const LABEL_COLORS = {
  bullish: '#16a34a',
  positive: '#22c55e',
  neutral: '#6b7280',
  cautious: '#f59e0b',
  bearish: '#ef4444',
};

function CustomTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const data = payload[0].payload;
  const color = LABEL_COLORS[data.label] || '#6b7280';

  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-lg p-3 max-w-xs">
      <div className="flex items-center justify-between gap-3 mb-1">
        <span className="text-sm font-medium">{data.quarter} {data.year}</span>
        <span
          className="text-xs font-medium px-2 py-0.5 rounded-full capitalize"
          style={{ backgroundColor: color + '15', color }}
        >
          {data.label}
        </span>
      </div>
      <div className="text-lg font-semibold mb-1" style={{ color }}>
        {data.score > 0 ? '+' : ''}{data.score.toFixed(2)}
      </div>
      {data.summary && (
        <p className="text-xs text-gray-500 leading-relaxed">{data.summary}</p>
      )}
    </div>
  );
}

export default function SentimentChart({ data, loading, company, analysis, trend }) {
  if (loading) {
    return (
      <div className="mt-6 bg-white border border-gray-200 rounded-xl p-5 animate-pulse">
        <div className="h-4 bg-gray-200 rounded w-48 mb-4" />
        <div className="h-48 bg-gray-100 rounded" />
      </div>
    );
  }

  if (!data || data.length === 0) return null;

  const chartData = data.map(d => ({
    ...d,
    name: `${d.quarter} ${d.year}`,
  }));

  return (
    <div className="mt-6 bg-white border border-gray-200 rounded-xl p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-medium text-gray-900">
          Sentiment Analysis: {company}
        </h3>
        {trend && (
          <span className="text-xs px-2.5 py-1 rounded-full bg-gray-100 text-gray-600 capitalize">
            Trend: {trend}
          </span>
        )}
      </div>

      <div className="h-56">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData} margin={{ top: 5, right: 5, bottom: 5, left: -20 }}>
            <defs>
              <linearGradient id="sentimentGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.2} />
                <stop offset="95%" stopColor="#F97316" stopOpacity={0.05} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis
              dataKey="name"
              tick={{ fontSize: 11, fill: '#9ca3af' }}
              tickLine={false}
              axisLine={{ stroke: '#e5e7eb' }}
            />
            <YAxis
              domain={[-1, 1]}
              ticks={[-1, -0.5, 0, 0.5, 1]}
              tick={{ fontSize: 11, fill: '#9ca3af' }}
              tickLine={false}
              axisLine={{ stroke: '#e5e7eb' }}
            />
            <Tooltip content={<CustomTooltip />} />
            <ReferenceLine y={0} stroke="#d1d5db" strokeDasharray="3 3" />
            <Area
              type="monotone"
              dataKey="score"
              stroke="#3B82F6"
              fill="url(#sentimentGradient)"
              strokeWidth={2}
              dot={{ r: 5, fill: '#3B82F6', stroke: '#fff', strokeWidth: 2 }}
              activeDot={{ r: 7, fill: '#F97316', stroke: '#fff', strokeWidth: 2 }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Quarter labels */}
      <div className="flex gap-2 mt-3 flex-wrap">
        {data.map((d, i) => {
          const color = LABEL_COLORS[d.label] || '#6b7280';
          return (
            <span
              key={i}
              className="text-xs px-2 py-0.5 rounded-full capitalize"
              style={{ backgroundColor: color + '12', color }}
            >
              {d.quarter} {d.year}: {d.label}
            </span>
          );
        })}
      </div>

      {analysis && (
        <p className="mt-3 text-sm text-gray-600 leading-relaxed">{analysis}</p>
      )}
    </div>
  );
}
