import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import './PlayerDetail.css';

const PlayerDetail = () => {
  const { playerId } = useParams();
  const [playerData, setPlayerData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchPlayerDetails = async () => {
      try {
        const response = await fetch(`/api/player/${playerId}`);
        if (!response.ok) {
          throw new Error('Player not found or error fetching details');
        }
        const data = await response.json();
        setPlayerData(data.data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchPlayerDetails();
  }, [playerId]);

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error}</div>;
  if (!playerData) return <div>No player data found.</div>;

  const renderStats = (stats) => {
    if (!stats) return <p>No statistics available.</p>;
    return (
      <div className="stats-grid">
        {stats.details.map(stat => (
          <div key={stat.id} className="stat-item">
            <span className="stat-name">{stat.type.name}:</span>
            <span className="stat-value">{stat.value.total ?? JSON.stringify(stat.value)}</span>
          </div>
        ))}
      </div>
    );
  };

  return (
    <div className="player-detail-container">
      <div className="player-header">
        <img src={playerData.image_path} alt={playerData.display_name} className="player-image" />
        <h1>{playerData.display_name}</h1>
      </div>
      <div className="player-bio">
        <p><strong>Full Name:</strong> {playerData.name}</p>
        <p><strong>Position:</strong> {playerData.position_name}</p>
        <p><strong>Birthdate:</strong> {playerData.date_of_birth}</p>
        <p><strong>Height:</strong> {playerData.height} cm</p>
      </div>

      {playerData.statistics && playerData.statistics.map(seasonStats => (
        <div key={seasonStats.id} className="season-stats">
          <h2>
            {seasonStats.season ? seasonStats.season.name : seasonStats.season_id}
            {seasonStats.season && seasonStats.season.league && ` - ${seasonStats.season.league.name}`}
          </h2>
          {renderStats(seasonStats)}
        </div>
      ))}
    </div>
  );
};

export default PlayerDetail; 