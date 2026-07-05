import { useEffect, useState } from 'react';
import { Upload, Trash2, BookOpen } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface Comic {
  id: string;
  title: string;
  totalPages: number;
  progressPage: number;
  progressPanel: number;
}

export default function Library({ onSelectComic }: { onSelectComic: (id: string) => void }) {
  const [comics, setComics] = useState<Comic[]>([]);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);

  const fetchComics = async () => {
    try {
      const res = await fetch(`${API_URL}/api/comics`);
      const data = await res.json();
      setComics(data);
    } catch (err) {
      console.error("Error loading library", err);
    }
  };

  useEffect(() => {
    fetchComics();
  }, []);

  const handleUpload = async (file: File) => {
    setUploading(true);
    const formData = new FormData();
    formData.append("file", file);
    try {
      const res = await fetch(`${API_URL}/api/comics/import`, {
        method: 'POST',
        body: formData,
      });
      if (res.ok) {
        fetchComics();
      } else {
        alert("Failed to import. Make sure it is a valid CBZ or CBR archive.");
      }
    } catch (err) {
      console.error("Upload failed", err);
      alert("Error uploading file.");
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm("Delete this comic?")) return;
    try {
      await fetch(`${API_URL}/api/comics/${id}`, { method: 'DELETE' });
      fetchComics();
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div 
      style={{ padding: '2rem', minHeight: '100vh', position: 'relative' }}
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragging(false);
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
          handleUpload(e.dataTransfer.files[0]);
        }
      }}
    >
      {dragging && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(30,30,30,0.85)', color: 'white', display: 'flex',
          flexDirection: 'column', alignItems: 'center', justifyContent: 'center', zIndex: 100
        }}>
          <h1 className="title-font" style={{ fontSize: '3rem', margin: '0 0 1rem 0' }}>Drop to Import</h1>
          <p style={{ fontSize: '1.2rem' }}>Only CBZ, CBR, ZIP, and RAR formats are supported.</p>
        </div>
      )}

      {uploading && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(30,30,30,0.7)', color: 'white', display: 'flex',
          flexDirection: 'column', alignItems: 'center', justifyContent: 'center', zIndex: 100
        }}>
          <h1 className="title-font" style={{ fontSize: '2.5rem' }}>Extracting & Indexing...</h1>
        </div>
      )}

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2.5rem' }}>
        <div>
          <h1 className="title-font" style={{ fontSize: '3.5rem', margin: 0, color: 'var(--crimson)', WebkitTextStroke: '2px var(--border-ink)' }}>CHIKA</h1>
          <h2 className="title-font" style={{ fontSize: '1.2rem', margin: '-5px 0 0 0', color: 'var(--text-ink)', letterSpacing: '2px' }}>Agam Katha Reader</h2>
        </div>
        <label className="retro-button">
          <Upload size={18} />
          Import Comic
          <input type="file" accept=".cbz,.cbr,.zip,.rar" onChange={(e) => {
            if (e.target.files && e.target.files[0]) handleUpload(e.target.files[0]);
          }} style={{ display: 'none' }} />
        </label>
      </div>

      {comics.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '6rem 0', background: 'rgba(255,255,255,0.4)', border: '4px dashed var(--border-ink)', borderRadius: '8px' }}>
          <BookOpen size={64} style={{ color: 'var(--text-ink)', marginBottom: '1.5rem', opacity: 0.7 }} />
          <p style={{ fontSize: '1.4rem', fontWeight: 600, margin: '0 0 0.5rem 0' }}>Your Library is Empty</p>
          <p style={{ fontSize: '1rem', opacity: 0.8 }}>Drag & drop CBZ/CBR files here or click "Import Comic" to upload.</p>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: '2.5rem' }}>
          {comics.map((comic) => {
            const progressPct = comic.totalPages > 1 
              ? Math.round((comic.progressPage / (comic.totalPages - 1)) * 100) 
              : 0;
            return (
              <div 
                key={comic.id} 
                onClick={() => onSelectComic(comic.id)}
                className="retro-border"
                style={{
                  background: 'white', cursor: 'pointer',
                  position: 'relative', overflow: 'hidden', display: 'flex', flexDirection: 'column'
                }}
              >
                <div style={{ position: 'relative', width: '100%', height: '280px', background: '#e5e5e5' }}>
                  <img 
                    src={`${API_URL}/api/comics/${comic.id}/cover`} 
                    alt={comic.title}
                    style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
                  />
                  {progressPct > 0 && (
                    <div style={{
                      position: 'absolute', top: '12px', right: '12px', background: 'var(--ochre)',
                      color: 'black', padding: '0.3rem 0.6rem', fontSize: '0.8rem', fontWeight: 'bold',
                      border: '2px solid var(--border-ink)', borderRadius: '12px', boxShadow: '2px 2px 0px var(--border-ink)'
                    }}>
                      {progressPct}% READ
                    </div>
                  )}
                </div>
                
                <div style={{ padding: '1rem', borderTop: '3px solid var(--border-ink)', flexGrow: 1, display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
                  <h3 style={{ margin: '0 0 0.75rem 0', fontSize: '1.1rem', fontWeight: 800, color: 'var(--text-ink)', overflow: 'hidden', textOverflow: 'ellipsis', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', lineHeight: '1.3' }}>
                    {comic.title.replace(/\.[^/.]+$/, "")}
                  </h3>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: '0.9rem', fontWeight: 600, color: 'gray' }}>{comic.totalPages} pages</span>
                    <button 
                      onClick={(e) => handleDelete(comic.id, e)} 
                      style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--crimson)', padding: '0.25rem' }}
                    >
                      <Trash2 size={18} />
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
