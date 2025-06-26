import React from 'react';

const PlayerOnPitch = ({ player }) => {
  if (!player) {
    return null;
  }

  // The FPL API does not reliably provide shirt images,
  // so we'll use the official Premier League badges as a fallback.
  const badgeUrl = `https://resources.premierleague.com/premierleague/badges/70/t${player.team_code}.png`;

  return (
    <div className="player-on-pitch">
      <div className="player-badge">
        <img src={badgeUrl} alt={`${player.team_name} badge`} />
      </div>
      <div className="player-info">
        <span className="player-name">{player.web_name}</span>
        <span className="player-points">{player.total_points} pts</span>
      </div>
    </div>
  );
};

export default PlayerOnPitch; 