import React from 'react';
import './Squad.css';

const Squad = ({ squad, onRemovePlayer, budget, remainingBudget }) => {
  const positions = ['GKP', 'DEF', 'MID', 'FWD'];

  const renderPosition = (position) => {
    const playersInPosition = squad.filter(p => p.position_name === position);
    return (
      <div key={position} className="squad-position">
        <h3>{position}</h3>
        {playersInPosition.map(player => (
          <div key={player.id} className="squad-player">
            <span>{player.web_name} ({player.team_name})</span>
            <button onClick={() => onRemovePlayer(player)}>Remove</button>
          </div>
        ))}
      </div>
    );
  };

  return (
    <div className="squad-container">
      <h2>Your Squad</h2>
      <div className="squad-details">
        <p>Total Cost: £{(budget - remainingBudget).toFixed(1)}m</p>
        <p>Remaining Budget: £{remainingBudget.toFixed(1)}m</p>
      </div>
      <div className="squad-grid">
        {positions.map(pos => renderPosition(pos))}
      </div>
    </div>
  );
};

export default Squad; 