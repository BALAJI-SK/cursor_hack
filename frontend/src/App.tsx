import { useState } from 'react';
import Library from './components/Library';
import Reader from './components/Reader';

export default function App() {
  const [selectedComicId, setSelectedComicId] = useState<string | null>(null);

  return (
    <div>
      {selectedComicId ? (
        <Reader comicId={selectedComicId} onBack={() => setSelectedComicId(null)} />
      ) : (
        <Library onSelectComic={setSelectedComicId} />
      )}
    </div>
  );
}
