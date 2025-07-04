import React, { useState, useEffect, useCallback } from 'react';
import { useLocation, Link } from 'react-router-dom';
import Pitch from './Pitch';
import Loading from './Loading';
import './SquadAnalysisPage.css';

const SquadAnalysisPage = () => {
    const location = useLocation();
    const { squad } = location.state || {};
    const [analysis, setAnalysis] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [newSquad, setNewSquad] = useState([]);
    const [highlightedIds, setHighlightedIds] = useState({ out: [], in: [] });

    const fetchAnalysis = useCallback(async () => {
        if (!squad) {
            setError("No squad data found. Please go back and build a squad first.");
            setLoading(false);
            return;
        }

        setLoading(true);
        setError(null);

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

            // --- Construct the new squad and highlighted players ---
            let tempSquad = [...squad];
            const outIds = data.suggested_transfers.map(t => t.player_out.id);
            const inIds = data.suggested_transfers.map(t => t.player_in.id);
            
            const playersToRemove = new Set(outIds);
            const playersToAdd = data.suggested_transfers.map(t => t.player_in);

            tempSquad = tempSquad.filter(p => !playersToRemove.has(p.id));
            tempSquad.push(...playersToAdd);

            setNewSquad(tempSquad);
            setHighlightedIds({ out: outIds, in: inIds });
            
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    }, [squad]);

    useEffect(() => {
        fetchAnalysis();
    }, [fetchAnalysis]);

    if (loading) {
        return (
            <Loading 
                title="Analyzing Your Squad..."
                subtext="The AI is running the numbers, checking fixture difficulty, and identifying the best possible transfers for your team."
            />
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

    const isWildcard = analysis.chip_suggestion?.chip === 'Wildcard';
    const suggestedSquad = isWildcard ? analysis.chip_suggestion.details.suggested_squad : newSquad;

    return (
        <div className="analysis-container">
            <Link to="/" className="back-link">&larr; Back to Home</Link>
            <h1>Squad Analysis & Suggestions</h1>
            <button onClick={fetchAnalysis} className="reevaluate-button" disabled={loading}>Re-evaluate</button>
            <div className="side-by-side-container">
                <div className="pitch-wrapper">
                    <h3>Your Current Squad</h3>
                    <Pitch squad={squad} highlightedPlayers={isWildcard ? squad.map(p => p.id) : highlightedIds.out} highlightColor="red" grayscaleUnchanged={true}/>
                </div>
                <div className="pitch-wrapper">
                    <h3>Suggested Squad</h3>
                    <Pitch squad={suggestedSquad} highlightedPlayers={isWildcard ? suggestedSquad.map(p => p.id) : highlightedIds.in} highlightColor="purple" grayscaleUnchanged={true}/>
                </div>
            </div>

            <div className="analysis-details-wrapper">
                {analysis.chip_suggestion && (
                    <div className="analysis-section chip-suggestion-section">
                        <h2>🔥 Strategic Chip Suggestion</h2>
                        <div className="suggestion-card chip-card">
                            <h3>{analysis.chip_suggestion.chip} Recommended!</h3>
                            <p>{analysis.chip_suggestion.reason}</p>
                        </div>
                    </div>
                )}

                <div className="analysis-section">
                    <h2>Captaincy Picks</h2>
                    <div className="captaincy-container">
                        {analysis.captain_suggestion && (
                            <div className="suggestion-card captain-card">
                                <div className="captain-label">CAPTAIN (C)</div>
                                <p className="captain-name">{analysis.captain_suggestion.web_name}</p>
                                <p className="captain-team">{analysis.captain_suggestion.team_name}</p>
                            </div>
                        )}
                        {analysis.vice_captain_suggestion && (
                            <div className="suggestion-card captain-card vice-captain-card">
                                <div className="captain-label">VICE-CAPTAIN (V)</div>
                                <p className="captain-name">{analysis.vice_captain_suggestion.web_name}</p>
                                <p className="captain-team">{analysis.vice_captain_suggestion.team_name}</p>
                            </div>
                        )}
                    </div>
                </div>

                {analysis.double_transfer_suggestion && (
                    <div className="analysis-section">
                        <h2>Strategic Double Transfer</h2>
                        <div className="suggestion-card transfer-card">
                            {analysis.double_transfer_suggestion.players_out.map((p_out, index) => {
                                const p_in = analysis.double_transfer_suggestion.players_in[index];
                                return (
                                    <div className="transfer-details" key={p_out.id}>
                                        <div className="player-out">
                                            <div className="transfer-header">OUT</div>
                                            <div className="player-name">{p_out.web_name}</div>
                                            <div className="player-team">{p_out.team_name}</div>
                                        </div>
                                        <div className="transfer-arrow">→</div>
                                        <div className="player-in">
                                            <div className="transfer-header">IN</div>
                                            <div className="player-name">{p_in.web_name}</div>
                                            <div className="player-team">{p_in.team_name}</div>
                                        </div>
                                    </div>
                                );
                            })}
                            <div className="transfer-summary">
                                <div className="score-gain-container">
                                    <div className="score-gain-header">Total AI Score Gain</div>
                                    <div className="score-gain-value">+{analysis.double_transfer_suggestion.score_gain.toFixed(1)}</div>
                                </div>
                                {analysis.double_transfer_suggestion.reason && (
                                    <div className="transfer-reason">
                                        <p>{analysis.double_transfer_suggestion.reason}</p>
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                )}

                <div className="analysis-section">
                    <h2>Top Transfer Suggestions</h2>
                    {analysis.suggested_transfers.map((transfer, index) => (
                      <div className="suggestion-card transfer-card" key={index}>
                        <div className="transfer-details">
                          <div className="player-out">
                            <div className="transfer-header">OUT</div>
                            <div className="player-name">{transfer.player_out.web_name}</div>
                            <div className="player-team">{transfer.player_out.team_name}</div>
                          </div>
                          <div className="transfer-arrow">→</div>
                          <div className="player-in">
                            <div className="transfer-header">IN</div>
                            <div className="player-name">{transfer.player_in.web_name}</div>
                            <div className="player-team">{transfer.player_in.team_name}</div>
                          </div>
                        </div>
                        <div className="score-gain-container">
                            <div className="score-gain-header">AI Score Gain</div>
                            <div className="score-gain-value">+{transfer.score_gain.toFixed(1)}</div>
                        </div>
                        {transfer.reason && (
                          <div className="transfer-reason">
                            <p>{transfer.reason}</p>
                          </div>
                        )}
                      </div>
                    ))}
                     {analysis.suggested_transfers.length === 0 && (
                        <div className="suggestion-card">
                            <p>No immediate transfers suggested. Your squad is looking strong!</p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default SquadAnalysisPage; 