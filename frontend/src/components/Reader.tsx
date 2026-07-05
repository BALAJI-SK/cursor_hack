import { useEffect, useState, useRef, SyntheticEvent } from 'react';
import { ArrowLeft, ArrowLeftRight, Eye, Volume2, VolumeX, Settings } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface PanelRect {
  left: number;
  top: number;
  right: number;
  bottom: number;
  audioUrl?: string | null;
  sfxUrl?: string | null;
}

export default function Reader({ comicId, onBack }: { comicId: string; onBack: () => void }) {
  const [page, setPage] = useState(0);
  const [panels, setPanels] = useState<PanelRect[]>([]);
  const [slot, setSlot] = useState(0); // 0 = intro, 1..len = panels, len + 1 = outro
  const [totalPages, setTotalPages] = useState(1);
  const [rtl, setRtl] = useState(false);
  const [showWhole, setShowWhole] = useState(false);
  const [loadingPanels, setLoadingPanels] = useState(false);

  const [isMuted, setIsMuted] = useState<boolean>(() => {
    return localStorage.getItem('chika_is_muted') === 'true';
  });
  const [enableNarrator, setEnableNarrator] = useState<boolean>(() => {
    return localStorage.getItem('chika_enable_narrator') !== 'false';
  });
  const [enableSfx, setEnableSfx] = useState<boolean>(() => {
    return localStorage.getItem('chika_enable_sfx') !== 'false';
  });
  const [showAudioSettings, setShowAudioSettings] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setShowAudioSettings(false);
      }
    };
    document.addEventListener('click', handleClickOutside);
    return () => {
      document.removeEventListener('click', handleClickOutside);
    };
  }, []);

  // Audio refs
  const sfxAudioRef = useRef<HTMLAudioElement | null>(null);
  const dialogueAudioRef = useRef<HTMLAudioElement | null>(null);
  const dialogueTimeoutRef = useRef<any>(null);

  // Save settings to localStorage
  useEffect(() => {
    localStorage.setItem('chika_is_muted', String(isMuted));
  }, [isMuted]);

  useEffect(() => {
    localStorage.setItem('chika_enable_narrator', String(enableNarrator));
  }, [enableNarrator]);

  useEffect(() => {
    localStorage.setItem('chika_enable_sfx', String(enableSfx));
  }, [enableSfx]);

  // Audio Manager Playback Orchestration
  useEffect(() => {
    // Stop any active audio playbacks immediately to prevent overlap
    if (sfxAudioRef.current) {
      sfxAudioRef.current.pause();
      sfxAudioRef.current = null;
    }
    if (dialogueAudioRef.current) {
      dialogueAudioRef.current.pause();
      dialogueAudioRef.current = null;
    }
    if (dialogueTimeoutRef.current) {
      clearTimeout(dialogueTimeoutRef.current);
      dialogueTimeoutRef.current = null;
    }

    if (isMuted) return;

    const p = panels[slot - 1];
    if (!p) return;

    // Start playing the SFX audio file if present and enabled
    if (p.sfxUrl && enableSfx) {
      const sfx = new Audio(API_URL + p.sfxUrl);
      sfxAudioRef.current = sfx;
      sfx.play().catch((err) => {
        console.warn("Failed to play SFX audio:", err);
      });
    }

    // Schedule playing the dialogue narration audio if present and enabled
    if (p.audioUrl && enableNarrator) {
      const playDialogue = () => {
        const audio = new Audio(API_URL + p.audioUrl);
        dialogueAudioRef.current = audio;
        audio.play().catch((err) => {
          console.warn("Failed to play dialogue audio:", err);
        });
      };

      if (p.sfxUrl && enableSfx) {
        dialogueTimeoutRef.current = setTimeout(playDialogue, 300);
      } else {
        playDialogue();
      }
    }

    // Cleanup active audios on unmount or before next run
    return () => {
      if (sfxAudioRef.current) {
        sfxAudioRef.current.pause();
      }
      if (dialogueAudioRef.current) {
        dialogueAudioRef.current.pause();
      }
      if (dialogueTimeoutRef.current) {
        clearTimeout(dialogueTimeoutRef.current);
      }
    };
  }, [slot, page, panels, isMuted, enableNarrator, enableSfx]);

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
    if (!p) {
      return {
        transform: 'translate(0px, 0px) scale(1)',
        transformOrigin: 'center center'
      };
    }
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
    <div style={{ 
      height: '100vh', 
      background: '#121212', 
      backgroundImage: 'radial-gradient(rgba(255,255,255,0.04) 0.8px, transparent 0.8px)',
      backgroundSize: '12px 12px',
      display: 'flex', 
      flexDirection: 'column', 
      color: 'white', 
      position: 'relative', 
      overflow: 'hidden' 
    }}>
      
      {/* Reader Header */}
      <div 
        className="glass-controls"
        style={{ 
          position: 'absolute', top: '1.25rem', left: '1.25rem', right: '1.25rem',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '0.6rem 1.25rem', zIndex: 20 
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <button 
            onClick={onBack} 
            className="retro-button" 
            style={{ padding: '0.35rem 0.75rem', background: 'var(--bg-cream)', color: 'var(--text-ink)', boxShadow: '2px 2px 0px var(--border-ink)', border: '2px solid var(--border-ink)' }}
          >
            <ArrowLeft size={16} />
            Library
          </button>
          <span className="title-font" style={{ fontSize: '1.1rem', color: 'var(--bg-cream)', letterSpacing: '1px' }}>
            PAGE {page + 1} OF {totalPages}
          </span>
        </div>

        <div style={{ display: 'flex', gap: '0.75rem' }}>
          <button 
            onClick={() => setIsMuted(!isMuted)} 
            className="retro-button" 
            style={{ 
              padding: '0.35rem 0.75rem', 
              background: isMuted ? 'var(--crimson)' : 'var(--bg-cream)', 
              color: isMuted ? 'white' : 'var(--text-ink)', 
              boxShadow: '2px 2px 0px var(--border-ink)', 
              border: '2px solid var(--border-ink)' 
            }}
            title={isMuted ? "Unmute sound" : "Mute sound"}
          >
            {isMuted ? <VolumeX size={16} /> : <Volume2 size={16} />}
            {isMuted ? "MUTED" : "SOUND ON"}
          </button>
          
          <div 
            ref={dropdownRef}
            style={{ position: 'relative' }}
          >
            <button 
              onClick={() => setShowAudioSettings(!showAudioSettings)} 
              className="retro-button" 
              style={{ 
                padding: '0.35rem 0.75rem', 
                background: 'var(--bg-cream)', 
                color: 'var(--text-ink)', 
                boxShadow: '2px 2px 0px var(--border-ink)', 
                border: '2px solid var(--border-ink)' 
              }}
              title="Audio Settings"
            >
              <Settings size={16} />
              AUDIO
            </button>
            {showAudioSettings && (
              <div 
                className="glass-controls title-font"
                style={{
                  position: 'absolute',
                  top: 'calc(100% + 8px)',
                  right: 0,
                  minWidth: '180px',
                  padding: '0.75rem',
                  zIndex: 50,
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '0.6rem',
                  color: 'var(--bg-cream)',
                  fontSize: '0.85rem',
                  letterSpacing: '1px'
                }}
              >
                <label style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', cursor: 'pointer', userSelect: 'none' }}>
                  <input 
                    type="checkbox" 
                    checked={enableNarrator} 
                    onChange={(e) => setEnableNarrator(e.target.checked)}
                    style={{ 
                      cursor: 'pointer',
                      accentColor: 'var(--crimson)',
                      width: '16px',
                      height: '16px',
                      border: '2px solid var(--border-ink)'
                    }}
                  />
                  Narrator Voice
                </label>
                <label style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', cursor: 'pointer', userSelect: 'none' }}>
                  <input 
                    type="checkbox" 
                    checked={enableSfx} 
                    onChange={(e) => setEnableSfx(e.target.checked)}
                    style={{ 
                      cursor: 'pointer',
                      accentColor: 'var(--crimson)',
                      width: '16px',
                      height: '16px',
                      border: '2px solid var(--border-ink)'
                    }}
                  />
                  SFX Sounds
                </label>
              </div>
            )}
          </div>

          <button 
            onClick={() => setRtl(!rtl)} 
            className="retro-button" 
            style={{ 
              padding: '0.35rem 0.75rem', 
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
              padding: '0.35rem 0.75rem', 
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
          width: '100vw', height: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
          overflow: 'hidden'
        }}>
          <img 
            src={`${API_URL}/api/comics/${comicId}/pages/${page}`} 
            alt={`Page ${page + 1}`}
            onLoad={handleImageLoad}
            style={{ 
              maxWidth: '92%', maxHeight: '92%', width: 'auto', height: 'auto',
              border: '4px solid var(--border-ink)', background: 'white',
              boxShadow: '10px 10px 0px rgba(0,0,0,0.5)',
              transition: 'transform 0.45s cubic-bezier(0.19, 1, 0.22, 1), transform-origin 0.45s cubic-bezier(0.19, 1, 0.22, 1)',
              ...getTransform()
            }}
          />
        </div>

        {/* Indicator details for debugging/checking panels count */}
        {loadingPanels && (
          <div 
            className="title-font"
            style={{
              position: 'absolute', bottom: '6.5rem', left: '2rem', background: 'var(--ochre)',
              color: 'black', border: '3px solid var(--border-ink)', padding: '0.5rem 1rem', borderRadius: '4px',
              boxShadow: '3px 3px 0px var(--border-ink)', fontSize: '0.9rem', fontWeight: 800, zIndex: 20, pointerEvents: 'none'
            }}
          >
            Running ML Panel Detection...
          </div>
        )}
        {panels.length > 0 && !showWhole && slot > 0 && slot <= panels.length && (
          <div 
            className="title-font"
            style={{
              position: 'absolute', bottom: '6.5rem', right: '2rem', background: 'var(--crimson)',
              color: 'white', border: '3px solid var(--border-ink)', padding: '0.5rem 1rem', borderRadius: '4px',
              boxShadow: '3px 3px 0px var(--border-ink)', fontSize: '0.9rem', fontWeight: 800, zIndex: 20, pointerEvents: 'none'
            }}
          >
            Panel {slot} of {panels.length}
          </div>
        )}
      </div>

      {/* Page Scrubber */}
      <div 
        className="glass-controls"
        style={{ 
          position: 'absolute', bottom: '1.25rem', left: '1.25rem', right: '1.25rem',
          padding: '1rem 1.5rem', 
          display: 'flex', alignItems: 'center', gap: '1.5rem', zIndex: 20 
        }}
      >
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
          className="retro-slider"
          style={{ 
            flexGrow: 1
          }}
        />
        <span className="title-font" style={{ fontSize: '1.1rem', minWidth: '60px', textAlign: 'right', color: 'var(--bg-cream)' }}>
          {page + 1} / {totalPages}
        </span>
      </div>
    </div>
  );
}
