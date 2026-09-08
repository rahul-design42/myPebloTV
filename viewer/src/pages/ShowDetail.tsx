import { useState, useMemo } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { api } from '../api/client';
import ImageWithFallback from '../components/ImageWithFallback';

export default function ShowDetail() {
  const { id } = useParams();
  
  const { data: catalog, isLoading, isError } = useQuery({
    queryKey: ['catalog'],
    queryFn: () => api.getCatalog(),
  });

  const show = useMemo(() => {
    if (!catalog?.sections) return null;
    for (const sec of catalog.sections) {
      const found = sec.shows?.find((s: any) => s.id === id);
      if (found) return found;
    }
    return null;
  }, [catalog, id]);

  if (isLoading) return <div className="loading-state">Loading show details...</div>;
  if (isError) return <div className="error-state">Failed to load show details.</div>;
  if (!show) return <div className="empty-state">Show not found.</div>;

  const trailers = show.seasons?.find((s: any) => s.season_number === 0);
  const normalSeasons = show.seasons?.filter((s: any) => s.season_number > 0) || [];

  return (
    <div>
      <div className="hero">
        <ImageWithFallback 
          src={show.artwork?.banner} 
          fallbackText="No Banner Available"
          className="hero-img" 
        />
        <div className="hero-content">
          <h1 className="hero-title">{show.title}</h1>
          <p style={{ maxWidth: '800px', fontSize: '1.2rem', marginBottom: '1.5rem' }}>
            {show.synopsis || 'No synopsis available.'}
          </p>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            {show.categories?.map((cat: string) => (
              <span key={cat} style={{ background: 'var(--primary)', padding: '0.25rem 0.75rem', borderRadius: '99px', fontSize: '0.875rem', fontWeight: 'bold' }}>
                {cat}
              </span>
            ))}
          </div>
        </div>
      </div>

      <div className="container" style={{ padding: '3rem 4%' }}>
        {trailers && trailers.episodes.length > 0 && (
          <div style={{ marginBottom: '3rem' }}>
            <h2 style={{ marginBottom: '1.5rem', color: 'var(--text-muted)' }}>Trailers</h2>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '1.5rem' }}>
              {trailers.episodes.map((ep: any) => (
                <EpisodeCard key={ep.content_group} episode={ep} />
              ))}
            </div>
          </div>
        )}

        {normalSeasons.map((season: any) => (
          <div key={season.id} style={{ marginBottom: '3rem' }}>
            <h2 style={{ marginBottom: '1.5rem' }}>Season {season.season_number}</h2>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {season.episodes.map((ep: any) => (
                <EpisodeCard key={ep.content_group} episode={ep} isHorizontal />
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function EpisodeCard({ episode, isHorizontal }: { episode: any, isHorizontal?: boolean }) {
  // Languages keys
  const availableLangs = Object.keys(episode.languages);
  const [selectedLang, setSelectedLang] = useState(availableLangs[0] || 'en');

  const langData = episode.languages[selectedLang];
  const thumbnail = langData?.artwork?.thumbnail;

  return (
    <div style={{ 
      display: 'flex', 
      flexDirection: isHorizontal ? 'row' : 'column', 
      gap: '1rem', 
      background: 'var(--surface)',
      borderRadius: '8px',
      overflow: 'hidden'
    }}>
      <div style={{ width: isHorizontal ? '300px' : '100%', flexShrink: 0 }}>
        <ImageWithFallback 
          src={thumbnail} 
          fallbackText={`${episode.title} Thumbnail`}
          className="thumbnail-img"
        />
      </div>
      <div style={{ padding: isHorizontal ? '1rem' : '0 1rem 1rem', display: 'flex', flexDirection: 'column', justifyContent: 'center', flex: 1 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <h3 style={{ fontSize: '1.25rem', marginBottom: '0.25rem' }}>
            {episode.episode_number}. {episode.title}
          </h3>
          <span style={{ color: 'var(--text-muted)' }}>{episode.duration_seconds}s</span>
        </div>
        
        {availableLangs.length > 1 && (
          <div style={{ marginTop: '1rem' }}>
            <label style={{ fontSize: '0.875rem', color: 'var(--text-muted)', marginRight: '0.5rem' }}>Audio:</label>
            <select 
              className="select" 
              style={{ padding: '0.25rem', fontSize: '0.875rem' }}
              value={selectedLang}
              onChange={e => setSelectedLang(e.target.value)}
            >
              {availableLangs.map(lang => (
                <option key={lang} value={lang}>{lang}</option>
              ))}
            </select>
          </div>
        )}
      </div>
    </div>
  );
}
