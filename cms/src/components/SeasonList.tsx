import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/client';
import { Plus, Trash2 } from 'lucide-react';
import EpisodeList from './EpisodeList';

export default function SeasonList({ showId }: { showId: string }) {
  const queryClient = useQueryClient();
  const [newSeasonNum, setNewSeasonNum] = useState<number | ''>('');
  const [activeSeason, setActiveSeason] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ['seasons', showId],
    queryFn: () => api.getSeasons(showId),
  });

  const createMutation = useMutation({
    mutationFn: (season_number: number) => api.createSeason(showId, { season_number }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['seasons', showId] });
      setNewSeasonNum('');
    },
    onError: (err: any) => alert(err.message)
  });

  const deleteMutation = useMutation({
    mutationFn: (seasonId: string) => api.deleteSeason(seasonId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['seasons', showId] });
      setActiveSeason(null);
    },
    onError: (err: any) => alert(err.message)
  });

  if (isLoading) return <div>Loading seasons...</div>;

  const seasons = data?.seasons || [];

  return (
    <div>
      <div className="header-flex" style={{ marginBottom: '1rem' }}>
        <h3>Seasons</h3>
        <form 
          onSubmit={(e) => {
            e.preventDefault();
            if (newSeasonNum !== '') createMutation.mutate(Number(newSeasonNum));
          }}
          style={{ display: 'flex', gap: '0.5rem' }}
        >
          <input 
            type="number" 
            className="input" 
            placeholder="Season number" 
            value={newSeasonNum} 
            onChange={e => setNewSeasonNum(e.target.value ? Number(e.target.value) : '')}
            style={{ width: '120px', margin: 0 }}
            required
            min={0}
          />
          <button type="submit" className="btn" disabled={createMutation.isPending}>
            <Plus size={16} /> Add
          </button>
        </form>
      </div>

      <div style={{ display: 'flex', gap: '1rem' }}>
        <div style={{ width: '250px', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          {seasons.map((season: any) => (
            <div 
              key={season.id}
              className={`card ${activeSeason === season.id ? 'active' : ''}`}
              style={{ 
                cursor: 'pointer', 
                padding: '1rem',
                border: activeSeason === season.id ? '2px solid var(--primary)' : '1px solid var(--border)'
              }}
              onClick={() => setActiveSeason(season.id)}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <strong style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  {season.season_number === 0 ? 'Trailer (Season 0)' : `Season ${season.season_number}`}
                </strong>
                <button 
                  className="btn btn-danger" 
                  style={{ padding: '0.25rem', borderRadius: '4px' }}
                  onClick={(e) => {
                    e.stopPropagation();
                    if (confirm('Delete season?')) deleteMutation.mutate(season.id);
                  }}
                  disabled={deleteMutation.isPending}
                >
                  <Trash2 size={14} />
                </button>
              </div>
            </div>
          ))}
          {seasons.length === 0 && <div style={{ color: 'var(--text-muted)' }}>No seasons yet.</div>}
        </div>

        <div style={{ flex: 1 }}>
          {activeSeason ? (
            <EpisodeList seasonId={activeSeason} />
          ) : (
            <div className="card" style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
              Select a season to manage episodes.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
