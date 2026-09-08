import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import { Search, Plus } from 'lucide-react';

export default function ShowsList() {
  const navigate = useNavigate();
  const [q, setQ] = useState('');
  const [section, setSection] = useState('');
  const [status, setStatus] = useState('');
  const [language, setLanguage] = useState('');
  const [page, setPage] = useState(1);
  const pageSize = 20;

  const { data, isLoading, isError, error } = useQuery<any>({
    queryKey: ['shows', { q, section, status, language, page }],
    queryFn: () => api.getShows({ q, section, status, language, page, page_size: pageSize }),
  });

  return (
    <div>
      <div className="header-flex">
        <h2>Shows</h2>
        <button className="btn" onClick={() => navigate('/shows/new')}>
          <Plus size={16} style={{ marginRight: '0.5rem' }} /> New Show
        </button>
      </div>

      <div className="card" style={{ marginBottom: '2rem' }}>
        <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
          <div style={{ flex: 1, minWidth: '200px' }}>
            <label className="label">Search Title</label>
            <div style={{ position: 'relative' }}>
              <input 
                type="text" 
                className="input" 
                value={q} 
                onChange={(e) => { setQ(e.target.value); setPage(1); }} 
                placeholder="Search..."
              />
              <Search size={16} style={{ position: 'absolute', right: '10px', top: '12px', color: 'var(--text-muted)' }} />
            </div>
          </div>
          <div style={{ width: '150px' }}>
            <label className="label">Section</label>
            <select className="select" value={section} onChange={(e) => { setSection(e.target.value); setPage(1); }}>
              <option value="">All</option>
              <option value="featured">Featured</option>
              <option value="series">Series</option>
              <option value="minisodes">Minisodes</option>
              <option value="songs">Songs</option>
            </select>
          </div>
          <div style={{ width: '150px' }}>
            <label className="label">Status</label>
            <select className="select" value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }}>
              <option value="">All</option>
              <option value="draft">Draft</option>
              <option value="published">Published</option>
              <option value="archived">Archived</option>
            </select>
          </div>
          <div style={{ width: '150px' }}>
            <label className="label">Language</label>
            <select className="select" value={language} onChange={(e) => { setLanguage(e.target.value); setPage(1); }}>
              <option value="">All</option>
              <option value="en">English (en)</option>
              <option value="hi">Hindi (hi)</option>
            </select>
          </div>
        </div>
      </div>

      {isLoading && <div>Loading shows...</div>}
      {isError && <div className="error-text">Failed to load shows: {(error as Error).message}</div>}

      {data && data.items && data.items.length === 0 && !isLoading && (
        <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)', background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '8px' }}>
          No shows found matching your filters.
        </div>
      )}

      {data && data.items && data.items.length > 0 && (
        <>
          <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
              <thead>
                <tr style={{ background: 'var(--bg)', borderBottom: '1px solid var(--border)' }}>
                  <th style={{ padding: '1rem' }}>Title</th>
                  <th style={{ padding: '1rem' }}>Slug</th>
                  <th style={{ padding: '1rem' }}>Section</th>
                  <th style={{ padding: '1rem' }}>Status</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((show: any) => (
                  <tr key={show.id} style={{ borderBottom: '1px solid var(--border)', cursor: 'pointer' }} onClick={() => navigate(`/shows/${show.id}`)}>
                    <td style={{ padding: '1rem', fontWeight: 500 }}>{show.title}</td>
                    <td style={{ padding: '1rem', color: 'var(--text-muted)' }}>{show.slug}</td>
                    <td style={{ padding: '1rem' }}>{show.section || '-'}</td>
                    <td style={{ padding: '1rem' }}>
                      <span style={{ 
                        padding: '0.25rem 0.5rem', 
                        borderRadius: '999px', 
                        fontSize: '0.875rem',
                        background: show.status === 'published' ? 'var(--success)' : (show.status === 'draft' ? '#f59e0b' : 'var(--text-muted)'),
                        color: 'white'
                      }}>
                        {show.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {data.total_pages > 1 && (
            <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', marginTop: '1.5rem', gap: '1rem' }}>
              <button 
                className="btn btn-secondary" 
                disabled={page === 1} 
                onClick={() => setPage(p => p - 1)}
              >
                Previous
              </button>
              <span>Page {page} of {data.total_pages}</span>
              <button 
                className="btn btn-secondary" 
                disabled={page === data.total_pages} 
                onClick={() => setPage(p => p + 1)}
              >
                Next
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
