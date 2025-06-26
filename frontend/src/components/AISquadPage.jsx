import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import '../App.css'; 
import Pitch from './Pitch';

const AISquadPage = () => {
  const [squadData, setSquadData] = useState({ 
    starting_11: [], 
    bench: [], 
    formation: '', 
    squad_value: 0, 
    remaining_budget: 0, 
    total_ai_score: 0 
  });
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

        {squadData.starting_11.length > 0 && (
          <>
            <div className="squad-info">
              <div className="formation-info">
                <h3>Formation: {squadData.formation}</h3>
              </div>
              <div className="squad-stats">
                <div className="stat-item">
                  <span className="stat-label">Squad Value:</span>
                  <span className="stat-value">£{squadData.squad_value}m</span>
                </div>
                <div className="stat-item">
                  <span className="stat-label">Remaining Budget:</span>
                  <span className="stat-value">£{squadData.remaining_budget}m</span>
                </div>
                <div className="stat-item">
                  <span className="stat-label">AI Score:</span>
                  <span className="stat-value">{squadData.total_ai_score}</span>
                </div>
              </div>
            </div>
            <Pitch starting_11={squadData.starting_11} bench={squadData.bench} />
          </>
        )}
      </div>
    </div>
  );
};

export default AISquadPage; 