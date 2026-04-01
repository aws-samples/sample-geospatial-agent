import { useState } from 'react';
import { v4 as uuidv4 } from 'uuid';
import { Grid } from '@cloudscape-design/components';
import { ChatSidebar } from '../components/ChatSidebar';
import { MapView } from '../components/MapView';
import type { ImageOverlay } from '../types';

export function Chat() {
  const [sessionId, setSessionId] = useState(uuidv4());
  const [drawnCoordinates, setDrawnCoordinates] = useState<number[][] | null>(null);
  const [imageOverlays, setImageOverlays] = useState<ImageOverlay[]>([]);
  const [resetTrigger, setResetTrigger] = useState(0);

  const handleSessionReset = () => {
    setSessionId(uuidv4());
    setDrawnCoordinates(null);
    setImageOverlays([]);
    setResetTrigger(prev => prev + 1);
  };

  const handleDrawnGeometry = (geojson: any) => {
    const feature = geojson.features[0];
    if (feature?.geometry?.type === 'Polygon') {
      setDrawnCoordinates(feature.geometry.coordinates[0]);
    } else if (feature?.geometry?.type === 'Point') {
      setDrawnCoordinates([feature.geometry.coordinates]);
    }
  };

  const handleDrawCleared = () => {
    setDrawnCoordinates(null);
  };

  const handleCoordinatesChange = (coords: number[][] | null) => {
    setDrawnCoordinates(coords);
  };

  return (
    <Grid gridDefinition={[{ colspan: 5 }, { colspan: 7 }]}>
      <ChatSidebar
        sessionId={sessionId}
        onSessionReset={handleSessionReset}
        coordinates={drawnCoordinates}
        onCoordinatesChange={handleCoordinatesChange}
        onOverlayAdd={(overlay) => setImageOverlays(prev => [...prev, overlay])}
      />
      <div style={{ height: 'calc(100vh - 40px)' }}>
        <MapView 
          onDrawnGeometry={handleDrawnGeometry}
          onDrawCleared={handleDrawCleared}
          imageOverlays={imageOverlays}
          resetTrigger={resetTrigger}
          coordinates={drawnCoordinates}
        />
      </div>
    </Grid>
  );
}
