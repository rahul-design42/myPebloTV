import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/client';
import SeasonList from '../components/SeasonList';
import ArtworkUpload from '../components/ArtworkUpload';
import { ArrowLeft, Save, Trash2 } from 'lucide-react';

export default function ShowEditor() {
  const { id } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const isNew = !id;

  const { data: show, isLoading } = useQuery({
    queryKey: ['show', id],
    queryFn: () => api.getShow(id!),
    enabled: !isNew,
  });

  const [formData, setFormData] = useState({
    title: '',
    slug: '',
    synopsis: '',
    section: '',
    status: 'draft',
    categories: [] as string[]
  });

  const [categoriesInput, setCategoriesInput] = useState('');

  useEffect(() => {
    if (show) {
      setFormData({
        title: show.title || '',
        slug: show.slug || '',
        synopsis: show.synopsis || '',
        section: show.section || '',
        status: show.status || 'draft',
        categories: show.categories || []
      });
      setCategoriesInput((show.categories || []).join(', '));
    }
  }, [show]);

  const saveMutation = useMutation({
    mutationFn: (data: any) => isNew ? api.createShow(data) : api.updateShow(id!, data),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ['shows'] });
      if (isNew) {
        navigate(`/shows/${res.id}`);
      } else {
        queryClient.invalidateQueries({ queryKey: ['show', id] });
        alert('Show saved successfully');
      }
    },
    onError: (err: any) => alert(err.message)
  });

  const deleteMutation = useMutation({
    mutationFn: () => api.deleteShow(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shows'] });
      navigate('/');
    },
    onError: (err: any) => alert(err.message)
  });

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    const categories = categoriesInput.split(',').map(c => c.trim()).filter(c => c);
    saveMutation.mutate({
      ...formData,
      categories,
      section: formData.section || null, // Handle nullable
    });
  };

  if (isLoading) return <div>Loading...</div>;

  return (
    <div>
      <div className="header-flex" style={{ marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <button className="btn btn-secondary" style={{ padding: '0.5rem' }} onClick={() => navigate('/')}>
            <ArrowLeft size={16} />
          </button>
          <h2 style={{ margin: 0 }}>{isNew ? 'New Show' : 'Edit Show'}</h2>
        </div>
        <div style={{ display: 'flex', gap: '1rem' }}>
          {!isNew && (
            <button 
              className="btn btn-danger" 
              onClick={() => { if (confirm('Delete show permanently?')) deleteMutation.mutate(); }}
              disabled={deleteMutation.isPending}
            >
              <Trash2 size={16} style={{ marginRight: '0.5rem' }} /> Delete Show
            </button>
          )}
          <button className="btn" onClick={handleSave} disabled={saveMutation.isPending}>
            <Save size={16} style={{ marginRight: '0.5rem' }} /> Save
          </button>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '2rem' }}>
        {/* Left Col: Form + Seasons */}
        <div>
          <div className="card" style={{ marginBottom: '2rem' }}>
            <h3 style={{ marginBottom: '1rem' }}>General Info</h3>
            <form onSubmit={handleSave}>
              <div className="form-group">
                <label className="label">Title</label>
                <input className="input" value={formData.title} onChange={e => setFormData({...formData, title: e.target.value})} required />
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                <div className="form-group">
                  <label className="label">Slug</label>
                  <input className="input" value={formData.slug} onChange={e => setFormData({...formData, slug: e.target.value})} required />
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
              <div className="form-group">
                <label className="label">Synopsis</label>
                <textarea className="textarea" rows={4} value={formData.synopsis} onChange={e => setFormData({...formData, synopsis: e.target.value})} />
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                <div className="form-group">
                  <label className="label">Section</label>
                  <select className="select" value={formData.section} onChange={e => setFormData({...formData, section: e.target.value})}>
                    <option value="">None</option>
                    <option value="featured">Featured</option>
                    <option value="series">Series</option>
                    <option value="minisodes">Minisodes</option>
                    <option value="songs">Songs</option>
                  </select>
                </div>
                <div className="form-group">
                  <label className="label">Categories (comma separated)</label>
                  <input className="input" value={categoriesInput} onChange={e => setCategoriesInput(e.target.value)} placeholder="e.g. Comedy, Action" />
                </div>
              </div>
              <button type="submit" style={{ display: 'none' }}>Submit</button>
            </form>
          </div>

          {!isNew && <SeasonList showId={id!} />}
        </div>

        {/* Right Col: Artwork */}
        <div>
          {!isNew ? (
            <div className="card">
              <h3 style={{ marginBottom: '1rem' }}>Artwork</h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                <ArtworkUpload 
                  showId={id!} 
                  kind="poster" 
                  existingArtwork={show?.artwork?.find((a: any) => a.kind === 'poster')} 
                />
                <ArtworkUpload 
                  showId={id!} 
                  kind="banner" 
                  existingArtwork={show?.artwork?.find((a: any) => a.kind === 'banner')} 
                />
              </div>
            </div>
          ) : (
            <div className="card" style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '3rem' }}>
              Save the show first to upload artwork and manage seasons.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
