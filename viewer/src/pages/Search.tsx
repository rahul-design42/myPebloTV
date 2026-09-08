import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../api/client';
import { Link } from 'react-router-dom';
import ImageWithFallback from '../components/ImageWithFallback';

export default function Search() {
  const [q, setQ] = useState('');
  const [category, setCategory] = useState('');
  const [language, setLanguage] = useState('');
  const [section, setSection] = useState('');

  const { data, isLoading, isError } = useQuery({
    queryKey: ['search', { q, category, language, section }],
    queryFn: () => api.searchCatalog({ q, category, language, section }),
  });

  return (
    <div className="container" style={{ marginTop: '2rem' }}>
      <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', marginBottom: '2rem' }}>
        <input 
          type="text" 
          className="input" 
          placeholder="Search titles..." 
          value={q} 
          onChange={e => setQ(e.target.value)} 
          style={{ flex: 1, minWidth: '200px' }}
        />
        <select className="select" value={category} onChange={e => setCategory(e.target.value)}>
          <option value="">All Categories</option>
          <option value="Comedy">Comedy</option>
          <option value="Action">Action</option>
          <option value="Drama">Drama</option>
          <option value="Sci-Fi">Sci-Fi</option>
        </select>
        <select className="select" value={section} onChange={e => setSection(e.target.value)}>
          <option value="">All Sections</option>
          <option value="featured">Featured</option>
          <option value="series">Series</option>
          <option value="minisodes">Minisodes</option>
          <option value="songs">Songs</option>
        </select>
        <select className="select" value={language} onChange={e => setLanguage(e.target.value)}>
          <option value="">All Languages</option>
          <option value="en">English (en)</option>
          <option value="hi">Hindi (hi)</option>
        </select>
      </div>

      {isLoading && <div className="loading-state">Searching...</div>}
      {isError && <div className="error-state">Search failed.</div>}

      {data && data.results && data.results.length === 0 && (
        <div className="empty-state">No results found for your search criteria.</div>
      )}

      {data && data.results && data.results.length > 0 && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '1.5rem' }}>
          {data.results.map((show: any) => (
            <Link to={`/shows/${show.id}`} key={show.id} style={{ display: 'block' }}>
              <ImageWithFallback 
                src={show.artwork?.poster} 
                fallbackText={show.title}
                className="poster-img"
                style={{ width: '100%', borderRadius: '4px', marginBottom: '0.5rem' }}
              />
              <h3 style={{ fontSize: '1rem', fontWeight: 'bold' }}>{show.title}</h3>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
