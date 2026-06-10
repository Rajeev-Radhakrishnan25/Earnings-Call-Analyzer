import React from 'react';

export default function Logo({ size = 34 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 72 72">
      <defs>
        <linearGradient id="logoGrad" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor="#F97316" />
          <stop offset="50%" stopColor="#8B5CF6" />
          <stop offset="100%" stopColor="#3B82F6" />
        </linearGradient>
      </defs>
      <polygon
        points="36,8 64,24 64,52 36,64 8,52 8,24"
        fill="none"
        stroke="url(#logoGrad)"
        strokeWidth="2.5"
        strokeLinejoin="round"
      />
      <line x1="36" y1="8" x2="36" y2="64" stroke="url(#logoGrad)" strokeWidth="0.8" opacity="0.2" />
      <line x1="8" y1="24" x2="64" y2="52" stroke="url(#logoGrad)" strokeWidth="0.8" opacity="0.2" />
      <line x1="64" y1="24" x2="8" y2="52" stroke="url(#logoGrad)" strokeWidth="0.8" opacity="0.2" />
      <polyline
        points="18,46 26,40 34,42 42,30 50,28 58,20"
        fill="none"
        stroke="url(#logoGrad)"
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="58" cy="20" r="3" fill="#3B82F6" />
      <circle cx="18" cy="46" r="2.5" fill="#F97316" />
      <circle cx="42" cy="30" r="2" fill="#8B5CF6" />
    </svg>
  );
}
