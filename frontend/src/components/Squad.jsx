import React from 'react';
import { useNavigate } from 'react-router-dom';
import './Squad.css';

const Squad = ({ squad, onRemovePlayer, budget, remainingBudget, squadRules }) => {
  const navigate = useNavigate();
  const positions = ['GKP', 'DEF', 'MID', 'FWD'];

  const handleAnalyzeClick = () => {
    navigate('/squad-analysis', { state: { squad: squad } });
  };

  const renderPosition = (position) => {
    const playersInPosition = squad.filter(p => p.position_name === position);
    return (
      <div key={position} className="squad-position">
        <h3>{position}</h3>
        <div className="squad-position-players">
          {playersInPosition.map(player => (
            <div key={player.id} className="squad-player">
              <div className="squad-player-info">
                {player.web_name} <span>({player.team_short_name})</span>
              </div>
              <button onClick={() => onRemovePlayer(player)} title="Remove player">&times;</button>
            </div>
          ))}
        </div>
      </div>
    );
  };

  return (
    <div className="squad-container">
      <h2>Your Squad</h2>
      <div className="squad-details">
        <div>
          <p className="detail-label">Total Cost</p>
          <p className="detail-value">£{(budget - remainingBudget).toFixed(1)}m</p>
        </div>
        <div>
          <p className="detail-label">Budget Left</p>
          <p className="detail-value">£{remainingBudget.toFixed(1)}m</p>
        </div>
      </div>
      {squad.length === squadRules.TOTAL_PLAYERS && (
        <button onClick={handleAnalyzeClick} className="analyze-button">
          Analyze Squad
        </button>
      )}
      <div className="squad-grid">
        {positions.map(pos => renderPosition(pos))}
      </div>
    </div>
  );
};

export default Squad; 