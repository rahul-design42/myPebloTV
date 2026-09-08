import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/client';
import { Upload, X, Loader2 } from 'lucide-react';

interface ArtworkUploadProps {
  showId?: string;
  episodeId?: string;
  kind: 'poster' | 'banner' | 'thumbnail';
  existingArtwork?: any;
  onSuccess?: () => void;
}

export default function ArtworkUpload({ showId, episodeId, kind, existingArtwork, onSuccess }: ArtworkUploadProps) {
  const queryClient = useQueryClient();
  const [error, setError] = useState('');
  
  const uploadMutation = useMutation({
    mutationFn: (file: File) => {
      const data = new FormData();
      data.append('file', file);
      data.append('kind', kind);
      if (showId) data.append('show_id', showId);
      if (episodeId) data.append('episode_id', episodeId);
      return api.uploadArtwork(data);
    },
    onSuccess: () => {
      setError('');
      if (showId) queryClient.invalidateQueries({ queryKey: ['show', showId] });
      if (episodeId) queryClient.invalidateQueries({ queryKey: ['seasons', showId] }); // Usually episode lists are fetched per season, might need specific invalidation based on parent usage
      if (onSuccess) onSuccess();
    },
    onError: (err: any) => {
      setError(err.message || 'Upload failed');
    }
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.deleteArtwork(id),
    onSuccess: () => {
      if (showId) queryClient.invalidateQueries({ queryKey: ['show', showId] });
      if (onSuccess) onSuccess();
    }
  });

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (file.size > 200 * 1024) {
      setError('File must be smaller than 200KB');
      return;
    }

    uploadMutation.mutate(file);
    e.target.value = '';
  };

  const getRequirements = () => {
    if (kind === 'poster') return '600x900 (2:3)';
    if (kind === 'banner') return '1280x720 (16:9)';
    if (kind === 'thumbnail') return '640x360 (16:9)';
    return '';
  };

  return (
    <div style={{ border: '1px dashed var(--border)', padding: '1rem', borderRadius: '8px', position: 'relative' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1rem' }}>
        <h4 style={{ textTransform: 'capitalize', margin: 0 }}>{kind}</h4>
        <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{getRequirements()} &middot; Max 200KB</span>
      </div>

      {error && <div className="error-text" style={{ marginBottom: '1rem' }}>{error}</div>}

      {existingArtwork ? (
        <div style={{ position: 'relative', display: 'inline-block' }}>
          <img 
            src={`http://localhost:8000/media/${existingArtwork.storage_key}`} 
            alt={kind} 
            style={{ 
              maxWidth: '100%', 
              maxHeight: '200px', 
              borderRadius: '4px',
              border: '1px solid var(--border)' 
            }} 
          />
          <button 
            type="button"
            className="btn btn-danger"
            style={{ position: 'absolute', top: 5, right: 5, padding: '0.25rem', borderRadius: '50%' }}
            onClick={() => {
              if (confirm('Delete this artwork?')) deleteMutation.mutate(existingArtwork.id);
            }}
            disabled={deleteMutation.isPending}
          >
            <X size={16} />
          </button>
        </div>
      ) : (
        <div style={{ textAlign: 'center', padding: '2rem 0' }}>
          {uploadMutation.isPending ? (
            <div style={{ color: 'var(--text-muted)' }}>
              <Loader2 className="spin" size={24} style={{ animation: 'spin 1s linear infinite' }} />
              <div style={{ marginTop: '0.5rem' }}>Uploading...</div>
            </div>
          ) : (
            <>
              <label style={{ cursor: 'pointer', color: 'var(--primary)', display: 'inline-flex', flexDirection: 'column', alignItems: 'center' }}>
                <Upload size={24} style={{ marginBottom: '0.5rem' }} />
                <span>Click to upload</span>
                <input 
                  type="file" 
                  accept="image/jpeg,image/png,image/webp" 
                  style={{ display: 'none' }} 
                  onChange={handleFileChange}
                />
              </label>
            </>
          )}
        </div>
      )}
      <style>{`
        @keyframes spin { 100% { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}
