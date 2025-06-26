import React from 'react';
import PlayerOnPitch from './PlayerOnPitch';
import './Pitch.css';

const Pitch = ({ starting_11, bench: benchPlayers }) => {
  if (!starting_11 || starting_11.length === 0) {
    return null;
  }

  // This object will hold the players for each position line
  const starters = { GKP: [], DEF: [], MID: [], FWD: [] };

  // Group the starting 11 by their positions
  for (const player of starting_11) {
    if (starters[player.position_name]) {
      starters[player.position_name].push(player);
    }
  }

  // Helper function to render a row of players on the pitch
  const renderPositionRow = (players) => {
    if (players.length === 0) return null;
    return (
      <div className="pitch-row">
        {players.map(player => <PlayerOnPitch key={player.id} player={player} />)}
      </div>
    );
  };

  return (
    <div className="pitch-container">
      <div className="pitch">
        {/* Render each position group in its own row */}
        {renderPositionRow(starters.GKP)}
        {renderPositionRow(starters.DEF)}
        {renderPositionRow(starters.MID)}
        {renderPositionRow(starters.FWD)}
      </div>
      <div className="bench">
        <h3>Bench</h3>
        <div className="bench-players">
            {/* Render the bench players */}
            {benchPlayers && benchPlayers.map(player => <PlayerOnPitch key={player.id} player={player} />)}
        </div>
      </div>
    </div>
  );
};

export default Pitch;