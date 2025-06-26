import React from 'react';
import './PlayerOnPitch.css';

const PlayerOnPitch = ({ player, isHighlighted, highlightColor, grayscale }) => {
  if (!player) {
    return null;
  }

  // The FPL API does not reliably provide shirt images,
  // so we'll use the official Premier League badges as a fallback.
  const badgeUrl = `https://resources.premierleague.com/premierleague/badges/70/t${player.team_code}.png`;

  const playerClasses = ['player-on-pitch'];
  if (grayscale) {
    playerClasses.push('grayscale');
  }

  const playerStyle = isHighlighted ? { 
    boxShadow: `0 0 10px 3px ${highlightColor}`,
  } : {};

  return (
    <div className={playerClasses.join(' ')} style={playerStyle}>
      <div className="player-badge">
        <img src={badgeUrl} alt={`${player.team_name} badge`} />
      </div>
      <div className="player-name-bar">
        <span>{player.web_name}</span>
      </div>
      <div className="player-points-bar">
        <span>{player.total_points} pts</span>
      </div>
    </div>
  );
};

export default PlayerOnPitch; 