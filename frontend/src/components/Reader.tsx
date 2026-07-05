import { useEffect, useState, useRef, SyntheticEvent } from 'react';
import { ArrowLeft, ArrowLeftRight, Eye } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface PanelRect {
  left: number;
  top: number;
  right: number;
  bottom: number;
}

export default function Reader({ comicId, onBack }: { comicId: string; onBack: () => void }) {
  const [page, setPage] = useState(0);
  const [panels, setPanels] = useState<PanelRect[]>([]);
  const [slot, setSlot] = useState(0); // 0 = intro, 1..len = panels, len + 1 = outro
  const [totalPages, setTotalPages] = useState(1);
  const [rtl, setRtl] = useState(false);
  const [showWhole, setShowWhole] = useState(false);
  const [loadingPanels, setLoadingPanels] = useState(false);

  const [containerSize, setContainerSize] = useState({ width: 0, height: 0 });
  const [imageSize, setImageSize] = useState({ width: 0, height: 0 });

  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    const observer = new ResizeObserver((entries) => {
      for (let entry of entries) {
        setContainerSize({
          width: entry.contentRect.width,
          height: entry.contentRect.height
        });
      }
    });
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);

  const handleImageLoad = (e: SyntheticEvent<HTMLImageElement>) => {
    const img = e.currentTarget;
    setImageSize({
      width: img.naturalWidth,
      height: img.naturalHeight
    });
  };

  // Load comic info and resume progress
  useEffect(() => {
    const loadComicProgress = async () => {
      try {
        const res = await fetch(`${API_URL}/api/comics`);
        const data = await res.json();
        const active = data.find((c: any) => c.id === comicId);
        if (active) {
          setTotalPages(active.totalPages);
          setPage(active.progressPage);
          setSlot(active.progressPanel);
        }
      } catch (err) {
        console.error("Error fetching progress", err);
      }
    };
    loadComicProgress();
  }, [comicId]);

  // Load panels when page changes
  useEffect(() => {
    const loadPanelsForPage = async () => {
      setLoadingPanels(true);
      try {
        const res = await fetch(`${API_URL}/api/comics/${comicId}/pages/${page}/panels?rtl=${rtl}`);
        if (res.ok) {
          const pData = await res.json();
          setPanels(pData);
          setSlot((currentSlot) => {
            if (currentSlot === -1) {
              return pData.length + 1; // Outro slot
            }
            return currentSlot;
          });
        }
      } catch (err) {
        console.error("Error loading panels", err);
        setPanels([]);
      } finally {
        setLoadingPanels(false);
      }
    };
    loadPanelsForPage();
  }, [comicId, page, rtl]);

  // Save progress to DB
  const saveProgress = async (p: number, s: number) => {
    try {
      await fetch(`${API_URL}/api/comics/${comicId}/progress`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ page: p, panel: s })
      });
    } catch (err) {
      console.error("Failed to save progress", err);
    }
  };

  const handleNext = () => {
    if (showWhole) {
      if (page < totalPages - 1) {
        setPage(page + 1);
        setSlot(0);
        saveProgress(page + 1, 0);
      }
      return;
    }

    const lastSlot = panels.length + 1;
    if (slot < lastSlot) {
      setSlot(slot + 1);
      saveProgress(page, slot + 1);
    } else {
      if (page < totalPages - 1) {
        setPage(page + 1);
        setSlot(0);
        saveProgress(page + 1, 0);
      }
    }
  };

  const handlePrev = () => {
    if (showWhole) {
      if (page > 0) {
        setPage(page - 1);
        setSlot(0);
        saveProgress(page - 1, 0);
      }
      return;
    }

    if (slot > 0) {
      setSlot(slot - 1);
      saveProgress(page, slot - 1);
    } else {
      if (page > 0) {
        setPage(page - 1);
        setSlot(-1); // Sentinel for OUTRO of previous page
        saveProgress(page - 1, -1);
      }
    }
  };

  // Calculate viewport transformation
  const getTransform = () => {
    if (slot === 0 || slot === panels.length + 1 || showWhole || panels.length === 0 || containerSize.width === 0 || imageSize.width === 0) {
      return {
        transform: 'translate(0px, 0px) scale(1)',
        transformOrigin: 'center center'
      };
    }
    
    const p = panels[slot - 1];
    const pw = p.right - p.left;
    const ph = p.bottom - p.top;
    const cx = (p.left + p.right) / 2;
    const cy = (p.top + p.bottom) / 2;

    // Determine the fitted image dimensions (contain fit)
    const containerAspect = containerSize.width / containerSize.height;
    const imageAspect = imageSize.width / imageSize.height;
    
    let wi = 0;
    let hi = 0;
    if (imageAspect > containerAspect) {
      // Width constrained
      wi = containerSize.width;
      hi = containerSize.width / imageAspect;
    } else {
      // Height constrained
      wi = containerSize.height * imageAspect;
      hi = containerSize.height;
    }

    // Scale to fit the panel inside the container (with a 92% fill padding for breathing room)
    const scaleX = containerSize.width / (pw * wi);
    const scaleY = containerSize.height / (ph * hi);
    const zoom = Math.min(scaleX, scaleY) * 0.92;

    // Translation to align panel center to container center
    const tx = wi * (0.5 - cx);
    const ty = hi * (0.5 - cy);

    return {
      transform: `translate(${tx}px, ${ty}px) scale(${zoom})`,
      transformOrigin: `${cx * 100}% ${cy * 100}%`
    };
  };

  return (
    <div style={{ height: '100vh', background: '#0a0a0a', display: 'flex', flexDirection: 'column', color: 'white', position: 'relative', overflow: 'hidden' }}>
      
      {/* Reader Header */}
      <div style={{ 
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '0.75rem 1.5rem', background: '#121212', borderBottom: '3px solid var(--border-ink)', zIndex: 10 
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <button 
            onClick={onBack} 
            className="retro-button" 
            style={{ padding: '0.4rem 0.8rem', background: 'var(--bg-cream)', color: 'var(--text-ink)', boxShadow: '2px 2px 0px var(--border-ink)', border: '2px solid var(--border-ink)' }}
          >
            <ArrowLeft size={16} />
            Library
          </button>
          <span className="title-font" style={{ fontSize: '1.2rem', color: 'var(--bg-cream)' }}>
            PAGE {page + 1} OF {totalPages}
          </span>
        </div>

        <div style={{ display: 'flex', gap: '0.75rem' }}>
          <button 
            onClick={() => setRtl(!rtl)} 
            className="retro-button" 
            style={{ 
              padding: '0.4rem 0.8rem', 
              background: rtl ? 'var(--ochre)' : 'var(--bg-cream)', 
              color: 'var(--text-ink)', 
              boxShadow: '2px 2px 0px var(--border-ink)', 
              border: '2px solid var(--border-ink)' 
            }}
          >
            <ArrowLeftRight size={16} />
            {rtl ? "RTL (MANGA)" : "LTR (WESTERN)"}
          </button>
          <button 
            onClick={() => {
              setShowWhole(!showWhole);
              setSlot(0);
              saveProgress(page, 0);
            }} 
            className="retro-button" 
            style={{ 
              padding: '0.4rem 0.8rem', 
              background: showWhole ? 'var(--crimson)' : 'var(--bg-cream)', 
              color: showWhole ? 'white' : 'var(--text-ink)', 
              boxShadow: '2px 2px 0px var(--border-ink)', 
              border: '2px solid var(--border-ink)' 
            }}
          >
            <Eye size={16} />
            {showWhole ? "PAGE VIEW" : "PANEL VIEW"}
          </button>
        </div>
      </div>

      {/* Reader Viewport */}
      <div 
        ref={containerRef}
        style={{ 
          flexGrow: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', 
          overflow: 'hidden', position: 'relative' 
        }}
      >
        {/* Transparent tap triggers */}
        <div 
          onClick={handlePrev} 
          style={{ position: 'absolute', left: 0, width: '25%', height: '100%', zIndex: 10, cursor: 'w-resize' }} 
          title="Previous Panel / Page"
        />
        <div 
          onClick={handleNext} 
          style={{ position: 'absolute', right: 0, width: '75%', height: '100%', zIndex: 10, cursor: 'e-resize' }} 
          title="Next Panel / Page"
        />

        {/* Viewport Frame with Zoom Math */}
        <div style={{
          width: '90vw', height: '80vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
          overflow: 'hidden'
        }}>
          <img 
            src={`${API_URL}/api/comics/${comicId}/pages/${page}`} 
            alt={`Page ${page + 1}`}
            onLoad={handleImageLoad}
            style={{ 
              maxWidth: '100%', maxHeight: '100%', width: 'auto', height: 'auto',
              border: '4px solid var(--border-ink)', background: 'white',
              transition: 'transform 0.35s cubic-bezier(0.25, 0.46, 0.45, 0.94)',
              ...getTransform()
            }}
          />
        </div>

        {/* Indicator details for debugging/checking panels count */}
        {loadingPanels && (
          <div style={{
            position: 'absolute', bottom: '15px', left: '15px', background: 'var(--ochre)',
            color: 'black', border: '2px solid var(--border-ink)', padding: '0.4rem 0.8rem', borderRadius: '4px',
            fontSize: '0.85rem', zIndex: 20, fontWeight: 'bold', pointerEvents: 'none'
          }}>
            Running ML Panel Detection...
          </div>
        )}
        {panels.length > 0 && !showWhole && slot > 0 && slot <= panels.length && (
          <div style={{
            position: 'absolute', bottom: '15px', right: '15px', background: 'rgba(0,0,0,0.85)',
            border: '2px solid var(--border-ink)', padding: '0.4rem 0.8rem', borderRadius: '4px',
            fontSize: '0.85rem', zIndex: 20, pointerEvents: 'none'
          }}>
            Panel {slot} of {panels.length}
          </div>
        )}
      </div>

      {/* Page Scrubber */}
      <div style={{ 
        padding: '1.25rem 2rem', background: '#121212', borderTop: '3px solid var(--border-ink)', 
        display: 'flex', alignItems: 'center', gap: '1.5rem', zIndex: 10 
      }}>
        <input 
          type="range" 
          min="0" 
          max={totalPages - 1} 
          value={page}
          onChange={(e) => {
            const newPage = parseInt(e.target.value);
            setPage(newPage);
            setSlot(0);
            saveProgress(newPage, 0);
          }}
          style={{ 
            flexGrow: 1, 
            accentColor: 'var(--crimson)', 
            height: '8px', 
            borderRadius: '4px', 
            cursor: 'pointer' 
          }}
        />
        <span className="title-font" style={{ fontSize: '1.1rem', minWidth: '60px', textAlign: 'right' }}>
          {page + 1} / {totalPages}
        </span>
      </div>
    </div>
  );
}
