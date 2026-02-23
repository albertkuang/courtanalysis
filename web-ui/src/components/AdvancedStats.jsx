import React, { useState } from 'react';
import axios from 'axios';
import {
    Trophy, Search, Activity, TrendingUp, ChevronRight, BarChart3,
    Target, Zap, PieChart as PieChartIcon, ArrowRight
} from 'lucide-react';
import {
    PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend
} from 'recharts';

const AdvancedStats = ({ currentPlayer }) => {
    const [activeTab, setActiveTab] = useState('prediction'); // 'prediction' | 'charting'

    return (
        <div className="space-y-6 animate-in fade-in duration-500">
            {/* Header Tabs */}
            <div className="bg-slate-900 p-2 rounded-xl border border-slate-800 flex gap-2">
                <button
                    onClick={() => setActiveTab('prediction')}
                    className={`flex-1 py-3 rounded-lg font-bold text-sm transition-all flex items-center justify-center gap-2 ${activeTab === 'prediction'
                            ? 'bg-gradient-to-r from-emerald-600 to-emerald-500 text-white shadow-lg'
                            : 'text-slate-400 hover:text-white hover:bg-slate-800'
                        }`}
                >
                    <Target className="w-4 h-4" /> Match Prediction
                </button>
                <button
                    onClick={() => setActiveTab('charting')}
                    className={`flex-1 py-3 rounded-lg font-bold text-sm transition-all flex items-center justify-center gap-2 ${activeTab === 'charting'
                            ? 'bg-gradient-to-r from-violet-600 to-violet-500 text-white shadow-lg'
                            : 'text-slate-400 hover:text-white hover:bg-slate-800'
                        }`}
                >
                    <BarChart3 className="w-4 h-4" /> Match Charting
                </button>
            </div>

            <div className="min-h-[500px]">
                {activeTab === 'prediction' ? (
                    <PredictionView currentPlayer={currentPlayer} />
                ) : (
                    <ChartingView currentPlayer={currentPlayer} />
                )}
            </div>
        </div>
    );
};

const PredictionView = ({ currentPlayer }) => {
    const [p1, setP1] = useState(currentPlayer?.id || ''); // ID or Name?
    const [p2, setP2] = useState('');
    const [prediction, setPrediction] = useState(null);
    const [loading, setLoading] = useState(false);

    // For simplicity, we assume IDs are passed. In real app, we need a player search/selector.
    // We'll use simple text inputs for IDs for Phase 3 Proof of Concept.

    const handlePredict = async (e) => {
        e.preventDefault();
        if (!p1 || !p2) return;

        setLoading(true);
        try {
            const res = await axios.get('/analysis/match_prediction', {
                params: { p1, p2 }
            });
            setPrediction(res.data);
        } catch (err) {
            console.error("Prediction failed:", err);
            // Mock error handling for demo
            alert("Prediction failed. Ensure Player IDs are valid.");
        }
        setLoading(false);
    };

    return (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* Input Section */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
                <h3 className="text-xl font-bold text-white mb-6 flex items-center gap-2">
                    <Zap className="w-5 h-5 text-emerald-400" /> Head-to-Head Forecast
                </h3>

                <form onSubmit={handlePredict} className="space-y-4">
                    <div>
                        <label className="text-xs text-slate-500 uppercase font-bold mb-1 block">Player 1 ID</label>
                        <input
                            type="text"
                            value={p1}
                            onChange={e => setP1(e.target.value)}
                            placeholder="Enter Player 1 ID..."
                            className="w-full bg-slate-950/50 border border-slate-700 rounded-lg p-3 text-white focus:border-emerald-500 focus:outline-none"
                        />
                    </div>

                    <div className="flex justify-center">
                        <div className="bg-slate-800 rounded-full p-2 border border-slate-700">
                            <ArrowRight className="w-4 h-4 text-slate-500 rotate-90 lg:rotate-0" />
                        </div>
                    </div>

                    <div>
                        <label className="text-xs text-slate-500 uppercase font-bold mb-1 block">Player 2 ID</label>
                        <input
                            type="text"
                            value={p2}
                            onChange={e => setP2(e.target.value)}
                            placeholder="Enter Player 2 ID..."
                            className="w-full bg-slate-950/50 border border-slate-700 rounded-lg p-3 text-white focus:border-emerald-500 focus:outline-none"
                        />
                    </div>

                    <button
                        type="submit"
                        disabled={loading}
                        className="w-full bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-3 rounded-lg mt-4 transition-colors disabled:opacity-50"
                    >
                        {loading ? 'Analyzing Matchup...' : 'Predict Outcome'}
                    </button>
                </form>
            </div>

            {/* Result Section */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 flex flex-col justify-center items-center relative overflow-hidden">
                {prediction ? (
                    <div className="w-full text-center space-y-6 relative z-10 animate-in zoom-in-95 duration-500">
                        <div className="flex justify-between items-center w-full px-4">
                            <div className="text-left">
                                <div className="text-sm text-slate-400">Player 1</div>
                                <div className="text-xl font-bold text-white max-w-[120px] truncate">{prediction.player1.name}</div>
                                <div className="text-emerald-400 font-mono text-sm">UTR {prediction.player1.utr}</div>
                            </div>
                            <div className="text-left text-right">
                                <div className="text-sm text-slate-400">Player 2</div>
                                <div className="text-xl font-bold text-white max-w-[120px] truncate">{prediction.player2.name}</div>
                                <div className="text-emerald-400 font-mono text-sm">UTR {prediction.player2.utr}</div>
                            </div>
                        </div>

                        {/* Win Probability Bar */}
                        <div className="py-8">
                            <div className="text-4xl font-bold text-white mb-2">
                                {prediction.player1.win_probability}%
                                <span className="text-lg text-slate-500 font-normal mx-2">vs</span>
                                {prediction.player2.win_probability}%
                            </div>
                            <div className="h-4 bg-slate-800 rounded-full overflow-hidden flex w-full max-w-md mx-auto">
                                <div
                                    className="bg-emerald-500 h-full transition-all duration-1000"
                                    style={{ width: `${prediction.player1.win_probability}%` }}
                                />
                                <div
                                    className="bg-rose-500 h-full transition-all duration-1000"
                                    style={{ width: `${prediction.player2.win_probability}%` }}
                                />
                            </div>
                            <div className="flex justify-between text-xs text-slate-500 mt-2 max-w-md mx-auto">
                                <span>{prediction.player1.name} Win Prob</span>
                                <span>{prediction.player2.name} Win Prob</span>
                            </div>
                        </div>

                        <div className="bg-slate-950/50 p-4 rounded-lg border border-slate-800 text-sm text-slate-400">
                            <span className="block font-bold text-slate-300 mb-1">Model: {prediction.model}</span>
                            {prediction.elo_prediction && (
                                <div className="mt-2 pt-2 border-t border-slate-800">
                                    <span className="block text-violet-400 font-bold mb-1">Elo Analysis</span>
                                    ELO favors {prediction.elo_prediction.player1_win_prob > 50 ? prediction.player1.name : prediction.player2.name}
                                    ({Math.max(prediction.elo_prediction.player1_win_prob, 100 - prediction.elo_prediction.player1_win_prob)}%)
                                </div>
                            )}
                        </div>
                    </div>
                ) : (
                    <div className="text-slate-600 text-center">
                        <Target className="w-16 h-16 mx-auto mb-4 opacity-20" />
                        <p className="text-lg">Enter IDs to see prediction</p>
                    </div>
                )}
            </div>
        </div>
    );
};

const ChartingView = ({ currentPlayer }) => {
    const [playerName, setPlayerName] = useState(currentPlayer?.name || '');
    const [chartData, setChartData] = useState(null); // List of matches
    const [playerStats, setPlayerStats] = useState(null); // Player overview stats
    const [selectedMatch, setSelectedMatch] = useState(null); // Detailed match data
    const [loading, setLoading] = useState(false);
    const [loadingMatch, setLoadingMatch] = useState(false);
    const [useDb, setUseDb] = useState(true); // Use database-backed data

    const fetchMatches = async (e) => {
        e?.preventDefault();
        if (!playerName) return;
        setLoading(true);
        try {
            if (useDb) {
                // Use database-backed API
                const gender = currentPlayer?.gender === 'M' ? 'ATP' : 'WTA';
                
                // Fetch player stats
                const statsRes = await axios.get(`/charting/players/${encodeURIComponent(playerName)}/stats`, {
                    params: { tour: gender }
                });
                setPlayerStats(statsRes.data);
                
                // Fetch matches
                const matchesRes = await axios.get('/charting/matches', {
                    params: { player_name: playerName, tour: gender }
                });
                setChartData({ matches: matchesRes.data.data, matchCount: matchesRes.data.count });
            } else {
                // Use legacy Tennis Abstract API
                const res = await axios.get('/integrations/tennis_abstract/charting', { params: { player_name: playerName } });
                setChartData(res.data);
            }
            setSelectedMatch(null);
        } catch (err) {
            console.error(err);
            alert("Failed to fetch charting data. Player might not have charting data.");
        }
        setLoading(false);
    };

    const loadMatchDetails = async (matchId) => {
        setLoadingMatch(true);
        try {
            let res;
            if (useDb) {
                // Use database-backed API
                res = await axios.get(`/charting/matches/${matchId}`);
            } else {
                // Use legacy API
                res = await axios.get(`/integrations/tennis_abstract/charting/${matchId}`);
            }
            setSelectedMatch(res.data);
        } catch (err) {
            console.error(err);
            alert("Failed to load match details.");
        }
        setLoadingMatch(false);
    };

    // Mock data for pie chart if no real detailed stats yet
    const shotDistribution = [
        { name: 'Forehand', value: 45, color: '#0ea5e9' },
        { name: 'Backhand', value: 35, color: '#8b5cf6' },
        { name: 'Serve', value: 20, color: '#10b981' },
    ];

    return (
        <div className="space-y-6">
            {/* Search Bar */}
            <div className="flex gap-2 items-center">
                <form onSubmit={fetchMatches} className="flex-1 flex gap-2">
                    <input
                        type="text"
                        value={playerName}
                        onChange={e => setPlayerName(e.target.value)}
                        placeholder="Search player charting data (e.g. 'Iga Swiatek')..."
                        className="flex-1 bg-slate-900 border border-slate-800 rounded-lg p-3 text-white focus:border-violet-500 focus:outline-none"
                    />
                    <button
                        type="submit"
                        disabled={loading}
                        className="bg-violet-600 hover:bg-violet-500 text-white font-bold px-6 rounded-lg transition-colors flex items-center gap-2"
                    >
                        {loading ? <Activity className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
                        Fetch
                    </button>
                </form>
                {/* Data Source Toggle */}
                <button
                    onClick={() => setUseDb(!useDb)}
                    className={`text-xs px-3 py-2 rounded-lg border ${useDb ? 'bg-emerald-900/30 border-emerald-700 text-emerald-400' : 'bg-slate-800 border-slate-700 text-slate-400'}`}
                    title={useDb ? 'Using database data' : 'Using live API data'}
                >
                    {useDb ? 'DB' : 'Live'}
                </button>
            </div>

            {/* Player Stats Summary */}
            {playerStats && playerStats.count > 0 && (
                <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
                    <h3 className="text-sm font-bold text-white mb-3 flex items-center gap-2">
                        <BarChart3 className="w-4 h-4 text-violet-400" /> 
                        Charting Stats for {playerStats.data[0]?.player_name}
                    </h3>
                    <div className="grid grid-cols-4 md:grid-cols-8 gap-3 text-center">
                        <div className="bg-slate-950 p-2 rounded-lg">
                            <div className="text-lg font-bold text-white">{playerStats.data[0]?.match_count || 0}</div>
                            <div className="text-xs text-slate-500">Matches</div>
                        </div>
                        <div className="bg-slate-950 p-2 rounded-lg">
                            <div className="text-lg font-bold text-emerald-400">{playerStats.data[0]?.aces || 0}</div>
                            <div className="text-xs text-slate-500">Aces</div>
                        </div>
                        <div className="bg-slate-950 p-2 rounded-lg">
                            <div className="text-lg font-bold text-rose-400">{playerStats.data[0]?.double_faults || 0}</div>
                            <div className="text-xs text-slate-500">DF</div>
                        </div>
                        <div className="bg-slate-950 p-2 rounded-lg">
                            <div className="text-lg font-bold text-blue-400">{playerStats.data[0]?.winners || 0}</div>
                            <div className="text-xs text-slate-500">Winners</div>
                        </div>
                        <div className="bg-slate-950 p-2 rounded-lg">
                            <div className="text-lg font-bold text-amber-400">{playerStats.data[0]?.unforced_errors || 0}</div>
                            <div className="text-xs text-slate-500">UE</div>
                        </div>
                        <div className="bg-slate-950 p-2 rounded-lg">
                            <div className="text-lg font-bold text-purple-400">{playerStats.data[0]?.first_serve_in || 0}</div>
                            <div className="text-xs text-slate-500">1st In</div>
                        </div>
                        <div className="bg-slate-950 p-2 rounded-lg">
                            <div className="text-lg font-bold text-cyan-400">{playerStats.data[0]?.break_points_saved || 0}</div>
                            <div className="text-xs text-slate-500">BP Saved</div>
                        </div>
                        <div className="bg-slate-950 p-2 rounded-lg">
                            <div className="text-lg font-bold text-orange-400">{playerStats.data[0]?.service_games_won || 0}</div>
                            <div className="text-xs text-slate-500">Sv Gms</div>
                        </div>
                    </div>
                </div>
            )}

            {chartData && (
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    {/* Matches List */}
                    <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden h-[600px] flex flex-col">
                        <div className="p-4 border-b border-slate-800 bg-slate-950/50">
                            <h3 className="font-bold text-white">Charted Matches ({chartData.matchCount})</h3>
                        </div>
                        <div className="overflow-y-auto flex-1 p-2 space-y-2">
                            {chartData.matches?.map((m) => (
                                <div
                                    key={m.matchId}
                                    onClick={() => loadMatchDetails(m.matchId)}
                                    className={`p-3 rounded-lg cursor-pointer border transition-all ${selectedMatch?.match_id === m.matchId
                                            ? 'bg-violet-900/20 border-violet-500/50'
                                            : 'bg-slate-800/50 border-slate-700 hover:border-slate-500'
                                        }`}
                                >
                                    <div className="text-xs text-slate-400 mb-1">{m.date} • {m.surface}</div>
                                    <div className="font-bold text-white text-sm">{m.player1} vs {m.player2}</div>
                                    <div className="text-xs text-slate-500 mt-1 truncate">{m.tournament}</div>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Match Details */}
                    <div className="lg:col-span-2 bg-slate-900 border border-slate-800 rounded-xl p-6 h-[600px] overflow-y-auto">
                        {loadingMatch ? (
                            <div className="flex flex-col items-center justify-center h-full text-slate-500">
                                <Activity className="w-8 h-8 animate-spin text-violet-500 mb-2" />
                                Parsing Shot-by-Shot Data...
                            </div>
                        ) : selectedMatch ? (
                            <div className="space-y-6">
                                {/* Match Header */}
                                <div className="border-b border-slate-800 pb-4">
                                    <h2 className="text-xl font-bold text-white">Match Analysis</h2>
                                    <div className="text-violet-400 text-sm mt-1 break-all">{selectedMatch.match_id}</div>
                                    {selectedMatch.url && (
                                        <a href={selectedMatch.url} target="_blank" rel="noopener noreferrer" className="text-xs text-slate-500 hover:text-white underline mt-2 block">
                                            View original on Tennis Abstract
                                        </a>
                                    )}
                                </div>

                                {/* Points Summary */}
                                <div className="grid grid-cols-3 gap-4">
                                    <div className="bg-slate-950 p-4 rounded-lg text-center border border-slate-800">
                                        <div className="text-2xl font-bold text-white">{selectedMatch.points_count || 0}</div>
                                        <div className="text-xs text-slate-500 uppercase">Points Charted</div>
                                    </div>
                                    {/* Placeholders for calculated stats */}
                                    <div className="bg-slate-950 p-4 rounded-lg text-center border border-slate-800">
                                        <div className="text-2xl font-bold text-emerald-400">-</div>
                                        <div className="text-xs text-slate-500 uppercase">Rally Length</div>
                                    </div>
                                    <div className="bg-slate-950 p-4 rounded-lg text-center border border-slate-800">
                                        <div className="text-2xl font-bold text-amber-400">-</div>
                                        <div className="text-xs text-slate-500 uppercase">Winners</div>
                                    </div>
                                </div>

                                {/* Visualization Placeholder */}
                                <div className="h-64 mt-4 relative">
                                    <h3 className="text-sm font-bold text-slate-400 mb-4">Shot Distribution (Demo)</h3>
                                    <ResponsiveContainer width="100%" height="100%">
                                        <PieChart>
                                            <Pie
                                                data={shotDistribution}
                                                cx="50%"
                                                cy="50%"
                                                innerRadius={60}
                                                outerRadius={80}
                                                paddingAngle={5}
                                                dataKey="value"
                                            >
                                                {shotDistribution.map((entry, index) => (
                                                    <Cell key={`cell-${index}`} fill={entry.color} />
                                                ))}
                                            </Pie>
                                            <Tooltip
                                                contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155' }}
                                                itemStyle={{ color: '#e2e8f0' }}
                                            />
                                            <Legend verticalAlign="bottom" height={36} />
                                        </PieChart>
                                    </ResponsiveContainer>
                                </div>

                                {/* Raw Points Sample */}
                                {selectedMatch.points && selectedMatch.points.length > 0 && (
                                    <div>
                                        <h3 className="text-sm font-bold text-slate-400 mb-2">Recent Points Log</h3>
                                        <div className="bg-slate-950 rounded-lg p-3 text-xs font-mono text-slate-400 overflow-x-auto">
                                            {/* Header */}
                                            <div className="flex gap-4 border-b border-slate-800 pb-1 mb-1 font-bold text-slate-300">
                                                <span className="w-8">Pt</span>
                                                <span className="w-12">Score</span>
                                                <span className="w-8">Svr</span>
                                                <span className="flex-1">Shot Sequence</span>
                                            </div>
                                            {selectedMatch.points.slice(0, 10).map((p, i) => (
                                                <div key={i} className="flex gap-4 py-1 border-b border-slate-800/50">
                                                    <span className="w-8 text-slate-500">{p.Pt}</span>
                                                    <span className="w-12 text-slate-300">{p.Pts}</span>
                                                    <span className="w-8 text-amber-400">{p.Svr}</span>
                                                    <span className="flex-1 truncate text-emerald-400/80" title={p['2nd'] || p['1st']}>
                                                        {p['2nd'] || p['1st'] || '-'}
                                                    </span>
                                                </div>
                                            ))}
                                            <div className="mt-2 text-center text-slate-600 italic">Showing first 10 points...</div>
                                        </div>
                                    </div>
                                )}
                            </div>
                        ) : (
                            <div className="flex flex-col items-center justify-center h-full text-slate-500">
                                <BarChart3 className="w-16 h-16 mb-4 opacity-20" />
                                <p>Select a match to view detailed analysis</p>
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
};

export default AdvancedStats;
