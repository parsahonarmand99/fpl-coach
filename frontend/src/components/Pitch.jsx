import React from 'react';
import PlayerOnPitch from './PlayerOnPitch';
import './Pitch.css';

const Pitch = ({ squad, starting_11, bench: benchPlayers, highlightedPlayers = [], highlightColor = 'green', grayscaleUnchanged = false }) => {
  const playersToShow = squad || starting_11;

  if (!playersToShow || playersToShow.length === 0) {
    return null;
  }

  // This object will hold the players for each position line
  const positionGroups = { GKP: [], DEF: [], MID: [], FWD: [] };

  // Group the players to show by their positions
  for (const player of playersToShow) {
    if (positionGroups[player.position_name]) {
      positionGroups[player.position_name].push(player);
    }
  }

  // Helper function to render a row of players on the pitch
  const renderPositionRow = (players) => {
    if (players.length === 0) return null;
    return (
      <div className="pitch-row">
        {players.map(player => {
            const isHighlighted = highlightedPlayers.includes(player.id);
            const shouldGrayscale = grayscaleUnchanged && !isHighlighted;
            return (
                <PlayerOnPitch 
                    key={player.id} 
                    player={player}
                    isHighlighted={isHighlighted}
                    highlightColor={highlightColor}
                    grayscale={shouldGrayscale}
                />
            )
        })}
      </div>
    );
  };

  return (
    <div className="pitch-container">
      <div className="pitch">
        {/* Render each position group in its own row */}
        {renderPositionRow(positionGroups.GKP)}
        {renderPositionRow(positionGroups.DEF)}
        {renderPositionRow(positionGroups.MID)}
        {renderPositionRow(positionGroups.FWD)}
      </div>
      {benchPlayers && benchPlayers.length > 0 && (
          <div className="bench">
            <h3>Bench</h3>
            <div className="bench-players">
                {/* Render the bench players */}
                {benchPlayers.map(player => <PlayerOnPitch key={player.id} player={player} />)}
            </div>
          </div>
      )}
    </div>
  );
};

export default Pitch;