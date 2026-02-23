import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
    GraduationCap, Loader2, RefreshCw, Trophy, TrendingUp, TrendingDown,
    Users, Calendar, MapPin, Medal, Star, Filter
} from 'lucide-react';

const ITFJuniorAnalysisView = ({ onPlayerClick }) => {
    const [finalists, setFinalists] = useState([]);
    const [improvedJuniors, setImprovedJuniors] = useState([]);
    const [recentWinners, setRecentWinners] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [activeTab, setActiveTab] = useState('finalists');
    const [selectedYear, setSelectedYear] = useState('All');

    const years = ['All', ...Array.from({ length: new Date().getFullYear() - 2015 + 1 }, (_, i) => 2015 + i).reverse()];

    useEffect(() => {
        fetchAll();
    }, [selectedYear]);

    const fetchAll = async () => {
        setLoading(true);
        setError(null);
        try {
            const params = { limit: 500 };
            if (selectedYear !== 'All') {
                params.year = selectedYear;
            }

            const [finalistsRes, improvedRes, winnersRes] = await Promise.all([
                axios.get('/api/highlights/junior_finalists', { params }).catch(() => ({ data: { data: [] } })),
                axios.get('/api/highlights/improved_juniors').catch(() => ({ data: { data: [] } })),
                axios.get('/api/highlights/recent_winners').catch(() => ({ data: { data: [] } })),
            ]);
            setFinalists(finalistsRes.data.data || []);
            setImprovedJuniors(improvedRes.data.data || []);
            setRecentWinners(winnersRes.data.data || []);
        } catch (err) {
            console.error('Error fetching ITF junior data:', err);
            setError('Failed to load ITF junior analysis data.');
        }
        setLoading(false);
    };

    const tabs = [
        { key: 'finalists', label: 'Junior Finalists', icon: Trophy, count: finalists.length },
        { key: 'improved', label: 'Most Improved', icon: TrendingUp, count: improvedJuniors.length },
        { key: 'winners', label: 'Recent Winners', icon: Medal, count: recentWinners.length },
    ];

    return (
        <div className="h-full flex flex-col animate-in fade-in duration-300">
            {/* Header */}
            <div className="p-4 md:p-6 border-b border-slate-800 bg-slate-900/50 backdrop-blur shrink-0">
                <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-3">
                        <GraduationCap className="w-6 h-6 text-indigo-400" />
                        <div>
                            <h1 className="text-xl font-bold text-white">ITF Junior Analysis</h1>
                            <p className="text-xs text-slate-500 mt-0.5">Track junior finalists, rising stars, and recent tournament winners</p>
                        </div>
                    </div>
                    <div className="flex items-center gap-2">
                        {/* Year Filter */}
                        <div className="relative">
                            <select
                                value={selectedYear}
                                onChange={(e) => setSelectedYear(e.target.value)}
                                className="appearance-none bg-slate-800 text-slate-300 text-sm px-3 py-2 pr-8 rounded-lg border border-slate-700 hover:border-slate-600 focus:outline-none focus:border-indigo-500 transition-colors cursor-pointer"
                            >
                                {years.map(year => (
                                    <option key={year} value={year}>{year}</option>
                                ))}
                            </select>
                            <Filter className="w-4 h-4 text-slate-500 absolute right-2.5 top-2.5 pointer-events-none" />
                        </div>

                        <button
                            onClick={fetchAll}
                            disabled={loading}
                            className="flex items-center gap-2 px-3 py-2 bg-indigo-500/10 text-indigo-400 rounded-lg hover:bg-indigo-500/20 transition-colors text-sm"
                        >
                            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                            Refresh
                        </button>
                    </div>
                </div>

                {/* Tabs */}
                <div className="flex gap-2">
                    {tabs.map(tab => (
                        <button
                            key={tab.key}
                            onClick={() => setActiveTab(tab.key)}
                            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${activeTab === tab.key
                                ? 'bg-indigo-500/20 text-indigo-400 border border-indigo-500/30'
                                : 'bg-slate-800 text-slate-400 hover:text-white border border-slate-700'
                                }`}
                        >
                            <tab.icon className="w-4 h-4" />
                            {tab.label}
                            <span className="text-[10px] bg-slate-700 px-1.5 py-0.5 rounded-full">{tab.count}</span>
                        </button>
                    ))}
                </div>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-4 md:p-6">
                {loading ? (
                    <div className="flex flex-col items-center justify-center h-64">
                        <Loader2 className="w-8 h-8 text-indigo-400 animate-spin" />
                        <span className="mt-3 text-slate-400 text-sm">Loading junior data...</span>
                    </div>
                ) : error ? (
                    <div className="bg-rose-500/10 border border-rose-500/30 rounded-lg p-6 text-center">
                        <p className="text-rose-400">{error}</p>
                    </div>
                ) : (
                    <>
                        {/* Junior Finalists Tab */}
                        {activeTab === 'finalists' && (
                            finalists.length === 0 ? (
                                <div className="flex flex-col items-center justify-center h-64 text-slate-500">
                                    <Trophy className="w-12 h-12 mb-4 opacity-20" />
                                    <p>No junior finalist data available for {selectedYear}</p>
                                </div>
                            ) : (
                                <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
                                    <table className="w-full text-left text-sm">
                                        <thead className="bg-slate-800/50 text-slate-400 uppercase text-xs font-semibold">
                                            <tr>
                                                <th className="px-4 py-3">Player</th>
                                                <th className="px-4 py-3">Tournament</th>
                                                <th className="px-4 py-3 text-center">Year</th>
                                                <th className="px-4 py-3 text-center">Round</th>
                                                <th className="px-4 py-3 text-right">Score</th>
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y divide-slate-800">
                                            {finalists.map((f, idx) => (
                                                <tr key={idx} className="hover:bg-slate-800/30 transition-colors">
                                                    <td className="px-4 py-3">
                                                        <span
                                                            className="text-white font-medium cursor-pointer hover:text-indigo-400 transition-colors"
                                                            onClick={() => onPlayerClick && onPlayerClick({ player_id: f.player_id || f.winner_id, name: f.player_name || f.winner_name })}
                                                        >
                                                            {f.player_name || f.winner_name || 'Unknown'}
                                                        </span>
                                                    </td>
                                                    <td className="px-4 py-3 text-slate-400">{f.tournament || '—'}</td>
                                                    <td className="px-4 py-3 text-center text-slate-400">{f.year || '—'}</td>
                                                    <td className="px-4 py-3 text-center">
                                                        <span className="bg-amber-500/20 text-amber-400 px-2 py-0.5 rounded text-xs font-bold">
                                                            {f.round || 'F'}
                                                        </span>
                                                    </td>
                                                    <td className="px-4 py-3 text-right text-amber-400 font-mono">{f.score || '—'}</td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            )
                        )}

                        {/* Most Improved Tab */}
                        {activeTab === 'improved' && (
                            improvedJuniors.length === 0 ? (
                                <div className="flex flex-col items-center justify-center h-64 text-slate-500">
                                    <TrendingUp className="w-12 h-12 mb-4 opacity-20" />
                                    <p>No improvement data available</p>
                                </div>
                            ) : (
                                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                    {improvedJuniors.map((player, idx) => (
                                        <div
                                            key={idx}
                                            className="bg-slate-900 border border-slate-800 rounded-xl p-4 hover:border-emerald-500/50 transition-all cursor-pointer"
                                            onClick={() => onPlayerClick && onPlayerClick({ player_id: player.player_id, name: player.name })}
                                        >
                                            <div className="flex items-start justify-between">
                                                <div>
                                                    <h3 className="font-bold text-white">{player.name}</h3>
                                                    <div className="flex items-center gap-2 mt-1 text-xs text-slate-400">
                                                        {player.country && <span>{player.country}</span>}
                                                        {player.age && <span>• Age {player.age}</span>}
                                                    </div>
                                                </div>
                                                <span className="text-xs bg-emerald-500/20 text-emerald-400 px-2 py-0.5 rounded-full font-bold">
                                                    #{idx + 1}
                                                </span>
                                            </div>
                                            <div className="mt-3 grid grid-cols-2 gap-3">
                                                <div>
                                                    <div className="text-xs text-slate-500">UTR</div>
                                                    <div className="text-lg font-bold text-emerald-400 font-mono">{player.utr_singles?.toFixed(2) || '—'}</div>
                                                </div>
                                                <div>
                                                    <div className="text-xs text-slate-500">Year Δ</div>
                                                    <div className={`text-lg font-bold font-mono flex items-center gap-1 ${player.year_delta > 0 ? 'text-emerald-400' : player.year_delta < 0 ? 'text-rose-400' : 'text-slate-400'}`}>
                                                        {player.year_delta > 0 ? <TrendingUp className="w-4 h-4" /> : player.year_delta < 0 ? <TrendingDown className="w-4 h-4" /> : null}
                                                        {player.year_delta > 0 ? '+' : ''}{player.year_delta?.toFixed(2) || '0.00'}
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )
                        )}

                        {/* Recent Winners Tab */}
                        {activeTab === 'winners' && (
                            recentWinners.length === 0 ? (
                                <div className="flex flex-col items-center justify-center h-64 text-slate-500">
                                    <Medal className="w-12 h-12 mb-4 opacity-20" />
                                    <p>No recent winner data available</p>
                                </div>
                            ) : (
                                <div className="space-y-3">
                                    {recentWinners.map((w, idx) => (
                                        <div key={idx} className="bg-slate-900 border border-slate-800 rounded-xl p-4">
                                            <div className="flex items-center justify-between">
                                                <div className="flex items-center gap-3">
                                                    <Medal className="w-5 h-5 text-amber-400" />
                                                    <div>
                                                        <span
                                                            className="text-white font-medium cursor-pointer hover:text-tennis-blue transition-colors"
                                                            onClick={() => onPlayerClick && onPlayerClick({ player_id: w.winner_id, name: w.winner_name })}
                                                        >
                                                            {w.winner_name}
                                                        </span>
                                                        <div className="text-xs text-slate-500 mt-0.5">{w.tournament}</div>
                                                    </div>
                                                </div>
                                                <div className="text-right">
                                                    <div className="text-amber-400 font-mono text-sm">{w.score}</div>
                                                    <div className="text-xs text-slate-500">{w.date}</div>
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )
                        )}
                    </>
                )}
            </div>
        </div>
    );
};

export default ITFJuniorAnalysisView;
