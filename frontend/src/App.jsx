import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import './App.css'
import Squad from './components/Squad'

const SQUAD_RULES = {
  TOTAL_PLAYERS: 15,
  BUDGET: 100.0,
  PLAYERS_PER_TEAM: 3,
  POSITIONS: {
    GKP: 2,
    DEF: 5,
    MID: 5,
    FWD: 3
  }
}

const Fixture = ({ fixture }) => {
  const difficultyClass = `difficulty-${fixture.difficulty}`;
  return (
    <div className={`fixture ${difficultyClass}`}>
      {fixture.opponent} ({fixture.is_home ? 'H' : 'A'})
    </div>
  );
};

function App() {
  const [players, setPlayers] = useState([])
  const [teams, setTeams] = useState([])
  const [positions, setPositions] = useState([])
  const [squad, setSquad] = useState([])

  const [sortKey, setSortKey] = useState('total_points')
  const [filterTeam, setFilterTeam] = useState('ALL')
  const [filterPosition, setFilterPosition] = useState('ALL')
  const [searchTerm, setSearchTerm] = useState('')
  const [isBuilding, setIsBuilding] = useState(false);

  useEffect(() => {
    fetch('/api/players')
      .then(response => response.json())
      .then(data => {
        setPlayers(data)
        // Get unique teams and positions from the data
        const teamNames = [...new Set(data.map(p => p.team_name))].sort()
        const positionNames = [...new Set(data.map(p => p.position_name))].sort()
        setTeams(teamNames)
        setPositions(positionNames)
      })
  }, [])

  const handleAddPlayer = (player) => {
    if (squad.length >= SQUAD_RULES.TOTAL_PLAYERS) {
      alert('Your squad is full.')
      return
    }

    if (squad.find(p => p.id === player.id)) {
      alert(`${player.web_name} is already in your squad.`)
      return
    }
    
    const currentBudget = squad.reduce((total, p) => total + p.now_cost, 0) / 10
    if (currentBudget + (player.now_cost / 10) > SQUAD_RULES.BUDGET) {
      alert('You do not have enough budget.')
      return
    }

    const playersFromSameTeam = squad.filter(p => p.team === player.team).length
    if (playersFromSameTeam >= SQUAD_RULES.PLAYERS_PER_TEAM) {
      alert(`You can only select ${SQUAD_RULES.PLAYERS_PER_TEAM} players from ${player.team_name}.`)
      return
    }

    const playersInPosition = squad.filter(p => p.position_name === player.position_name).length
    const maxInPosition = SQUAD_RULES.POSITIONS[player.position_name]
    if (playersInPosition >= maxInPosition) {
      alert(`You can only select ${maxInPosition} players in the ${player.position_name} position.`)
      return
    }

    setSquad([...squad, player])
  }

  const handleRemovePlayer = (player) => {
    setSquad(squad.filter(p => p.id !== player.id))
  }

  const handleBuildRandomSquad = async () => {
    setIsBuilding(true);
    try {
      const response = await fetch('/api/random-squad');
      if (!response.ok) {
        throw new Error("Failed to build a random squad. The server might be busy.");
      }
      const randomSquad = await response.json();
      setSquad(randomSquad);
    } catch (error) {
      alert(error.message);
    } finally {
      setIsBuilding(false);
    }
  };

  const sortedAndFilteredPlayers = players
    .filter(player => (filterTeam === 'ALL' || player.team_name === filterTeam))
    .filter(player => (filterPosition === 'ALL' || player.position_name === filterPosition))
    .filter(player => player.web_name.toLowerCase().includes(searchTerm.toLowerCase()))
    .sort((a, b) => {
      if (a[sortKey] > b[sortKey]) return -1
      if (a[sortKey] < b[sortKey]) return 1
      return 0
    })
  
  const squadCost = squad.reduce((total, p) => total + p.now_cost, 0) / 10
  const remainingBudget = SQUAD_RULES.BUDGET - squadCost

  return (
    <div className="App">
      <div className="main-content">
        <h1>FPL AI Coach</h1>

        <div className="controls">
          <div className="control-group">
            <label htmlFor="search">Search:</label>
            <input
              type="text"
              id="search"
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
              placeholder="Player name..."
            />
          </div>
          <div className="control-group">
            <label htmlFor="sort">Sort by:</label>
            <select id="sort" value={sortKey} onChange={e => setSortKey(e.target.value)}>
              <option value="total_points">Total Points</option>
              <option value="now_cost">Price</option>
              <option value="form">Form</option>
              <option value="goals_scored">Goals</option>
              <option value="assists">Assists</option>
            </select>
          </div>

          <div className="control-group">
            <label htmlFor="filter-team">Team:</label>
            <select id="filter-team" value={filterTeam} onChange={e => setFilterTeam(e.target.value)}>
              <option value="ALL">All Teams</option>
              {teams.map(team => <option key={team} value={team}>{team}</option>)}
            </select>
          </div>

          <div className="control-group">
            <label htmlFor="filter-position">Position:</label>
            <select id="filter-position" value={filterPosition} onChange={e => setFilterPosition(e.target.value)}>
              <option value="ALL">All Positions</option>
              {positions.map(pos => <option key={pos} value={pos}>{pos}</option>)}
            </select>
          </div>
          <div className="ai-buttons">
            <Link to="/ai-squad" className="ai-squad-button">
                Build AI Squad
            </Link>
            <button onClick={handleBuildRandomSquad} className="ai-squad-button" disabled={isBuilding}>
              {isBuilding ? 'Building...' : 'Build Randomized Squad'}
            </button>
          </div>
        </div>

        <div className="player-list">
          {sortedAndFilteredPlayers.map(player => (
            <Link to={`/player/${player.id}`} key={player.id} className="player-card-link">
              <div className="player-card">
                <h2>{player.web_name}</h2>
                <p className="player-team">{player.team_name}</p>
                <p className="player-position">{player.position_name}</p>
                <div className="player-stats">
                  <p data-label="Pts">{player.total_points}</p>
                  <p data-label="Price">£{(player.now_cost / 10).toFixed(1)}m</p>
                  <p data-label="Form">{player.form}</p>
                </div>
                <div className="upcoming-fixtures">
                  {player.upcoming_fixtures && player.upcoming_fixtures.map((fixture, index) => (
                    <Fixture key={index} fixture={fixture} />
                  ))}
                </div>
                <button onClick={(e) => {
                  e.preventDefault();
                  handleAddPlayer(player);
                }}>Add to Squad</button>
              </div>
            </Link>
          ))}
        </div>
      </div>
      <div className="sidebar">
        <Squad
          squad={squad}
          onRemovePlayer={handleRemovePlayer}
          budget={SQUAD_RULES.BUDGET}
          remainingBudget={remainingBudget}
          squadRules={SQUAD_RULES}
        />
      </div>
    </div>
  )
}

export default App
