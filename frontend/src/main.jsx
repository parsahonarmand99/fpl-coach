import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';
import App from './App.jsx'
import PlayerDetail from './components/PlayerDetail.jsx';
import AISquadPage from './components/AISquadPage.jsx';
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <Router>
      <Routes>
        <Route path="/" element={<App />} />
        <Route path="/player/:playerId" element={<PlayerDetail />} />
        <Route path="/ai-squad" element={<AISquadPage />} />
      </Routes>
    </Router>
  </React.StrictMode>,
)
