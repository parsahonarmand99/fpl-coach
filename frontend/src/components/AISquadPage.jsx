import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import '../App.css'; 
import Pitch from './Pitch';

const AISquadPage = () => {
  const [squadData, setSquadData] = useState({ starting_11: [], bench: [] });
  const [isAiLoading, setIsAiLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleBuildAiSquad = async () => {
    setIsAiLoading(true);
    setError(null);
    try {
      const response = await fetch('/api/ai-squad');
      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || 'Failed to build AI squad');
      }
      const aiSquad = await response.json();
      setSquadData(aiSquad);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsAiLoading(false);
    }
  };

  useEffect(() => {
    // Automatically build the squad when the page loads
    handleBuildAiSquad();
  }, []);

  return (
    <div className="App single-column-layout">
      <div className="main-content">
        <Link to="/" className="back-button">
          &larr; Back to Home
        </Link>
        <h1>AI Generated Squad</h1>
        
        <div className="squad-controls">
            <button onClick={handleBuildAiSquad} disabled={isAiLoading}>
              {isAiLoading ? 'Regenerating...' : 'Regenerate Squad'}
            </button>
        </div>

        {error && <div className="error-message">Error: {error}</div>}

        {isAiLoading && squadData.starting_11.length === 0 && (
          <div className="loading-message">
            Please wait, the AI is analyzing trillions of combinations to build your optimal team...
          </div>
        )}

        {squadData.starting_11.length > 0 && <Pitch starting_11={squadData.starting_11} bench={squadData.bench} />}
      </div>
    </div>
  );
};

export default AISquadPage; 