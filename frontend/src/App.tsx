import { useState } from 'react';
import { Home } from './pages/Home';
import { Detail } from './pages/Detail';

function App() {
  const [selectedSensor, setSelectedSensor] = useState<string | null>(null);

  const handleSensorClick = (serialNumber: string) => {
    setSelectedSensor(serialNumber);
  };

  const handleBack = () => {
    setSelectedSensor(null);
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {selectedSensor ? (
        <Detail 
          serialNumber={selectedSensor} 
          onBack={handleBack} 
        />
      ) : (
        <Home onSensorClick={handleSensorClick} />
      )}
    </div>
  );
}

export default App;
