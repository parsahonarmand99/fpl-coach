import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import Loading from './Loading';
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

  if (loading) return (
    <Loading 
      title="Loading Player Details..."
      subtext="Fetching the latest stats and performance data."
    />
  );
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
        <div className="player-header-info">
          <h1>{playerData.display_name}</h1>
          <p>{playerData.position_name}</p>
        </div>
      </div>
      <h2 className="section-title">Player Info</h2>
      <div className="player-bio">
        <div className="player-bio-item">
          <strong>Full Name</strong>
          {playerData.name}
        </div>
        <div className="player-bio-item">
          <strong>Date of Birth</strong>
          {playerData.date_of_birth}
        </div>
        <div className="player-bio-item">
          <strong>Height</strong>
          {playerData.height ? `${playerData.height} cm` : 'N/A'}
        </div>
        <div className="player-bio-item">
          <strong>Weight</strong>
          {playerData.weight ? `${playerData.weight} kg` : 'N/A'}
        </div>
      </div>

      {playerData.form_stats && playerData.form_stats.length > 0 && (
        <>
          <h2 className="section-title">Recent Form (Last 5 Games)</h2>
          <div className="table-container">
            <table className="form-table">
              <thead>
                <tr>
                  <th>Opponent</th>
                  <th>Date</th>
                  <th>Mins</th>
                  <th>G</th>
                  <th>A</th>
                  <th>YC</th>
                  <th>RC</th>
                  <th>Bonus</th>
                  <th>BPS</th>
                  <th>Pts</th>
                  <th>xG</th>
                  <th>xA</th>
                  <th>xGI</th>
                  <th>xGC</th>
                  <th>Clean Sheets</th>
                  <th>Goals Conceded</th>
                  <th>Own Goals</th>
                  <th>Penalties Saved</th>
                  <th>Penalties Missed</th>
                  <th>Saves</th>
                  <th>Influence</th>
                  <th>Creativity</th>
                  <th>Threat</th>
                  <th>ICT Index</th>
                </tr>
              </thead>
              <tbody>
                {playerData.form_stats.map(game => (
                  <tr key={game.fixture_id}>
                    <td>{game.fixture_name}</td>
                    <td>{new Date(game.date).toLocaleDateString()}</td>
                    <td>{game.minutes_played}</td>
                    <td>{game.goals}</td>
                    <td>{game.assists}</td>
                    <td>{game.yellow_cards}</td>
                    <td>{game.red_cards}</td>
                    <td>{game.bonus}</td>
                    <td>{game.bps}</td>
                    <td>{game.total_points}</td>
                    <td>{game.expected_goals}</td>
                    <td>{game.expected_assists}</td>
                    <td>{game.expected_goal_involvements}</td>
                    <td>{game.expected_goals_conceded}</td>
                    <td>{game.clean_sheets}</td>
                    <td>{game.goals_conceded}</td>
                    <td>{game.own_goals}</td>
                    <td>{game.penalties_saved}</td>
                    <td>{game.penalties_missed}</td>
                    <td>{game.saves}</td>
                    <td>{game.influence}</td>
                    <td>{game.creativity}</td>
                    <td>{game.threat}</td>
                    <td>{game.ict_index}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {playerData.statistics && playerData.statistics.map(seasonStats => (
        <div key={seasonStats.id} className="season-stats">
          <h2 className="section-title">
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