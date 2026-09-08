import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/client';
import { Plus, Trash2, Edit2, X } from 'lucide-react';
import ArtworkUpload from './ArtworkUpload';

export default function EpisodeList({ seasonId }: { seasonId: string }) {
  const queryClient = useQueryClient();
  const [editingId, setEditingId] = useState<string | null>(null);
  const [isCreating, setIsCreating] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ['episodes', seasonId],
    queryFn: () => api.getEpisodes(seasonId),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.deleteEpisode(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['episodes', seasonId] }),
    onError: (err: any) => alert(err.message)
  });

  if (isLoading) return <div>Loading episodes...</div>;
  const episodes = data?.episodes || [];

  return (
    <div className="card">
      <div className="header-flex" style={{ marginBottom: '1.5rem' }}>
        <h3 style={{ margin: 0 }}>Episodes</h3>
        <button className="btn" onClick={() => setIsCreating(true)} disabled={isCreating}>
          <Plus size={16} /> Add Episode
        </button>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        {isCreating && (
          <EpisodeForm 
            seasonId={seasonId} 
            onClose={() => setIsCreating(false)} 
            onSuccess={() => setIsCreating(false)} 
          />
        )}

        {episodes.map((ep: any) => (
          <div key={ep.id} style={{ border: '1px solid var(--border)', borderRadius: '8px', padding: '1rem' }}>
            {editingId === ep.id ? (
              <EpisodeForm 
                seasonId={seasonId} 
                initialData={ep} 
                onClose={() => setEditingId(null)} 
                onSuccess={() => setEditingId(null)} 
              />
            ) : (
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
                  <div>
                    <h4 style={{ margin: 0, fontSize: '1.1rem' }}>{ep.episode_number}. {ep.title}</h4>
                    <div style={{ color: 'var(--text-muted)', fontSize: '0.875rem', marginTop: '0.25rem' }}>
                      {ep.content_group} &middot; {ep.language} &middot; {ep.status} &middot; {ep.duration_seconds || 'No duration'}s
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <button className="btn btn-secondary" style={{ padding: '0.25rem 0.5rem' }} onClick={() => setEditingId(ep.id)}>
                      <Edit2 size={14} />
                    </button>
                    <button 
                      className="btn btn-danger" 
                      style={{ padding: '0.25rem 0.5rem' }} 
                      onClick={() => { if (confirm('Delete episode?')) deleteMutation.mutate(ep.id); }}
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>

                {/* Thumbnails list */}
                <div>
                  <h5 style={{ marginBottom: '0.5rem' }}>Thumbnail</h5>
                  <ArtworkUpload 
                    episodeId={ep.id} 
                    kind="thumbnail" 
                    existingArtwork={ep.artwork?.find((a: any) => a.kind === 'thumbnail')} 
                    onSuccess={() => queryClient.invalidateQueries({ queryKey: ['episodes', seasonId] })}
                  />
                </div>
              </div>
            )}
          </div>
        ))}

        {episodes.length === 0 && !isCreating && (
          <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '2rem' }}>
            No episodes in this season.
          </div>
        )}
      </div>
    </div>
  );
}

function EpisodeForm({ seasonId, initialData, onClose, onSuccess }: any) {
  const queryClient = useQueryClient();
  const [formData, setFormData] = useState({
    title: initialData?.title || '',
    episode_number: initialData?.episode_number ?? '',
    content_group: initialData?.content_group || '',
    language: initialData?.language || 'en',
    duration_seconds: initialData?.duration_seconds ?? '',
    status: initialData?.status || 'draft'
  });

  const mutation = useMutation({
    mutationFn: (data: any) => 
      initialData 
        ? api.updateEpisode(initialData.id, data)
        : api.createEpisode(seasonId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['episodes', seasonId] });
      onSuccess();
    },
    onError: (err: any) => alert(err.message)
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    mutation.mutate({
      ...formData,
      episode_number: Number(formData.episode_number),
      duration_seconds: formData.duration_seconds ? Number(formData.duration_seconds) : undefined,
    });
  };

  return (
    <form onSubmit={handleSubmit} style={{ background: 'var(--bg)', padding: '1rem', borderRadius: '4px', border: '1px solid var(--border)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1rem' }}>
        <h4 style={{ margin: 0 }}>{initialData ? 'Edit Episode' : 'New Episode'}</h4>
        <button type="button" onClick={onClose} style={{ background: 'transparent', border: 'none', cursor: 'pointer' }}><X size={16} /></button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
        <div className="form-group">
          <label className="label">Title</label>
          <input className="input" value={formData.title} onChange={e => setFormData({...formData, title: e.target.value})} required />
        </div>
        <div className="form-group">
          <label className="label">Episode Number</label>
          <input type="number" className="input" value={formData.episode_number} onChange={e => setFormData({...formData, episode_number: e.target.value})} required />
        </div>
        <div className="form-group">
          <label className="label">Content Group</label>
          <input className="input" value={formData.content_group} onChange={e => setFormData({...formData, content_group: e.target.value})} required />
        </div>
        <div className="form-group">
          <label className="label">Language</label>
          <select className="select" value={formData.language} onChange={e => setFormData({...formData, language: e.target.value})} required>
            <option value="en">English (en)</option>
            <option value="hi">Hindi (hi)</option>
          </select>
        </div>
        <div className="form-group">
          <label className="label">Duration (seconds)</label>
          <input type="number" className="input" value={formData.duration_seconds} onChange={e => setFormData({...formData, duration_seconds: e.target.value})} />
        </div>
        <div className="form-group">
          <label className="label">Status</label>
          <select className="select" value={formData.status} onChange={e => setFormData({...formData, status: e.target.value})} required>
            <option value="draft">Draft</option>
            <option value="published">Published</option>
            <option value="archived">Archived</option>
          </select>
        </div>
      </div>
      <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
        <button type="button" className="btn btn-secondary" onClick={onClose}>Cancel</button>
        <button type="submit" className="btn" disabled={mutation.isPending}>Save</button>
      </div>
    </form>
  );
}
