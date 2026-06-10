const API_BASE = '/api';

async function request(url, options = {}) {
  const response = await fetch(`${API_BASE}${url}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || 'Request failed');
  }
  return response.json();
}

export const api = {
  health: () => request('/health/ready'),
  seedingStatus: () => request('/seeding-status'),

  listCompanies: () => request('/companies'),
  searchCompanies: (q) => request(`/companies/search?q=${encodeURIComponent(q)}`),
  ingestCompany: (ticker) => request(`/companies/${ticker}/ingest`, { method: 'POST' }),
  ingestStatus: (ticker) => request(`/companies/${ticker}/ingest-status`),
  getStats: () => request('/stats'),

  query: (payload) => request('/query', {
    method: 'POST',
    body: JSON.stringify(payload),
  }),

  sentiment: (ticker) => request(`/query/sentiment?ticker=${encodeURIComponent(ticker)}`, {
    method: 'POST',
  }),
};
