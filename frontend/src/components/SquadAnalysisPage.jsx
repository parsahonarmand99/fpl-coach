import React, { useState, useEffect } from 'react';
import { useLocation, Link } from 'react-router-dom';
import './SquadAnalysisPage.css';

const SquadAnalysisPage = () => {
    const location = useLocation();
    const { squad } = location.state || {};
    const [analysis, setAnalysis] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        if (!squad) {
            setError("No squad data found. Please go back and build a squad first.");
            setLoading(false);
            return;
        }

        const fetchAnalysis = async () => {
            try {
                const response = await fetch('/api/analyze-squad', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ squad }),
                });
                if (!response.ok) {
                    const errData = await response.json();
                    throw new Error(errData.detail || "Failed to get analysis.");
                }
                const data = await response.json();
                setAnalysis(data);

            } catch (err) {
                setError(err.message);
            } finally {
                setLoading(false);
            }
        };

        fetchAnalysis();
    }, [squad]);

    if (loading) {
        return (
            <div className="analysis-container loading">
                <h2>Analyzing Your Squad...</h2>
                <p>The AI is running the numbers, checking fixture difficulty, and identifying the best possible transfers for your team.</p>
                <div className="spinner"></div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="analysis-container error">
                <h2>An Error Occurred</h2>
                <p>{error}</p>
                <Link to="/" className="back-link">Back to Home</Link>
            </div>
        );
    }
    
    if (!analysis) {
        return (
            <div className="analysis-container">
                <h2>No analysis data.</h2>
                <Link to="/" className="back-link">Back to Home</Link>
            </div>
        );
    }

    return (
        <div className="analysis-container">
            <Link to="/" className="back-link">&larr; Back to Home</Link>
            <h1>Squad Analysis & Suggestions</h1>

            <div className="analysis-section">
                <h2>Captaincy Pick</h2>
                <div className="suggestion-card captain-card">
                    <p className="captain-name">{analysis.captain_suggestion.web_name}</p>
                    <p className="captain-team">{analysis.captain_suggestion.team_name}</p>
                </div>
            </div>

            <div className="analysis-section">
                <h2>Top Transfer Suggestions</h2>
                {analysis.suggested_transfers.map((transfer, index) => (
                    <div key={index} className="suggestion-card transfer-card">
                        <div className="transfer-player-out">
                            <p className="label">OUT</p>
                            <p className="player-name">{transfer.player_out.web_name}</p>
                            <p className="team-name">{transfer.player_out.team_name}</p>
                        </div>
                        <div className="transfer-arrow">&rarr;</div>
                        <div className="transfer-player-in">
                            <p className="label">IN</p>
                            <p className="player-name">{transfer.player_in.web_name}</p>
                            <p className="team-name">{transfer.player_in.team_name}</p>
                        </div>
                        <div className="score-gain">
                            <p className="label">AI Score Gain</p>
                            <p className="score-value">+{transfer.score_gain.toFixed(1)}</p>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};

export default SquadAnalysisPage; 