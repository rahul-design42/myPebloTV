import { useQuery } from '@tanstack/react-query';
import { api } from '../api/client';
import { Link } from 'react-router-dom';
import ImageWithFallback from '../components/ImageWithFallback';

export default function Home() {
  const { data: catalog, isLoading, isError } = useQuery({
    queryKey: ['catalog'],
    queryFn: () => api.getCatalog(),
  });

  if (isLoading) return <div className="loading-state">Loading Catalogue...</div>;
  if (isError || !catalog) return <div className="error-state">Failed to load catalogue.</div>;

  const sections = catalog.sections || [];
  if (sections.length === 0) return <div className="empty-state">No content available.</div>;

  // Find a featured show for hero
  let heroShow = null;
  for (const sec of sections) {
    if (sec.shows && sec.shows.length > 0) {
      heroShow = sec.shows.find((s: any) => s.artwork?.banner);
      if (heroShow) break;
    }
  }
  if (!heroShow && sections[0]?.shows?.[0]) heroShow = sections[0].shows[0];

  return (
    <div>
      {heroShow && (
        <div className="hero">
          <ImageWithFallback 
            src={heroShow.artwork?.banner} 
            fallbackText="No Banner Available"
            className="hero-img" 
          />
          <div className="hero-content">
            <h1 className="hero-title">{heroShow.title}</h1>
            <p style={{ maxWidth: '600px', marginBottom: '1.5rem', color: '#ccc' }}>
              {heroShow.synopsis || 'No synopsis available.'}
            </p>
            <Link to={`/shows/${heroShow.id}`} className="btn">Watch Now</Link>
          </div>
        </div>
      )}

      <div style={{ marginTop: '-4rem', position: 'relative', zIndex: 10 }}>
        {sections.map((section: any) => (
          <div key={section.id} className="row">
            <h2 className="row-title">
              {section.id.charAt(0).toUpperCase() + section.id.slice(1)}
            </h2>
            <div className="row-posters">
              {section.shows.map((show: any) => (
                <Link to={`/shows/${show.id}`} key={show.id} className="poster-item">
                  <ImageWithFallback 
                    src={show.artwork?.poster} 
                    fallbackText={show.title}
                    className="poster-img"
                  />
                </Link>
              ))}
              {section.shows.length === 0 && (
                <div style={{ padding: '1rem', color: 'var(--text-muted)' }}>Empty section</div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
