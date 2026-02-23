
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Loader2, MapPin, Trophy, Calendar, Activity } from 'lucide-react';

const OngoingTournamentsView = ({ onPlayerClick }) => {
    const [tournaments, setTournaments] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchTournaments = async () => {
            try {
                const res = await axios.get('/api/tournaments/ongoing');
                setTournaments(res.data.data || []);
                setError(null);
            } catch (err) {
                console.error(err);
                if (err.response && err.response.status === 404) {
                    setError("API endpoint not found. The backend server needs to be restarted.")
                } else if (err.code === "ERR_NETWORK") {
                    setError("Cannot connect to backend. Please ensure the server is running.")
                } else {
                    setError("Failed to load tournaments. Please check console.")
                }
            }
            setLoading(false);
        };
        fetchTournaments();
    }, []);

    // Helper to get tournament type badge
    const getTournamentTypeBadge = (priority) => {
        switch (priority) {
            case 0:
                return <span className="text-[10px] bg-purple-500/20 text-purple-400 px-2 py-0.5 rounded-full border border-purple-500/30 font-bold">WTA/ATP</span>;
            case 1:
                return <span className="text-[10px] bg-blue-500/20 text-blue-400 px-2 py-0.5 rounded-full border border-blue-500/30 font-bold">ITF</span>;
            case 2:
                return <span className="text-[10px] bg-cyan-500/20 text-cyan-400 px-2 py-0.5 rounded-full border border-cyan-500/30 font-bold">ITF Junior</span>;
            case 3:
                return <span className="text-[10px] bg-amber-500/20 text-amber-400 px-2 py-0.5 rounded-full border border-amber-500/30 font-bold">College</span>;
            default:
                return <span className="text-[10px] bg-slate-500/20 text-slate-400 px-2 py-0.5 rounded-full border border-slate-500/30 font-bold">Other</span>;
        }
    };

    if (loading) {
        return (
            <div className="flex justify-center items-center py-20">
                <Loader2 className="animate-spin text-tennis-blue w-8 h-8" />
            </div>
        );
    }

    if (error) {
        return (
            <div className="flex flex-col items-center justify-center py-20 text-center">
                <div className="bg-rose-500/10 p-4 rounded-full mb-4">
                    <Activity className="w-8 h-8 text-rose-500" />
                </div>
                <h3 className="text-xl font-bold text-white mb-2">Connection Error</h3>
                <p className="text-slate-400 max-w-sm mb-6">{error}</p>
                <div className="text-xs text-slate-500 bg-slate-800 p-2 rounded mb-4 font-mono">
                    Endpoint: /api/tournaments/ongoing
                </div>
                <button
                    onClick={() => window.location.reload()}
                    className="px-4 py-2 bg-slate-800 hover:bg-slate-700 rounded-lg text-white text-sm font-medium transition-colors"
                >
                    Reload Page
                </button>
            </div>
        );
    }

    return (
        <div className="space-y-6 animate-in fade-in duration-500">
            <div className="flex items-center gap-3 mb-6 bg-slate-900 border border-slate-800 p-6 rounded-2xl shadow-lg">
                <div className="bg-tennis-blue/20 p-3 rounded-xl">
                    <MapPin className="w-8 h-8 text-tennis-blue" />
                </div>
                <div>
                    <h2 className="text-2xl font-bold text-white">Ongoing Tournaments</h2>
                    <p className="text-slate-400 text-sm">Active events from the last 7 days</p>
                </div>
            </div>

            <div className="space-y-6">
                {tournaments.length === 0 ? (
                    <div className="text-center text-slate-500 py-20 border-2 border-dashed border-slate-800 rounded-xl">
                        <Trophy className="w-12 h-12 mx-auto mb-4 opacity-20" />
                        <p className="text-lg">No active tournaments found in the last week.</p>
                        <p className="text-sm text-slate-600 mt-2">Try importing more recent match data.</p>
                    </div>
                ) : (
                    <div className="grid grid-cols-1 gap-6">
                        {tournaments.map((t, idx) => (
                            <div key={idx} className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-xl hover:shadow-2xl transition-shadow duration-300">
                                <div className="bg-gradient-to-r from-slate-900 to-slate-950 px-6 py-4 border-b border-slate-800 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                                    <div>
                                        <h3 className="text-lg font-bold text-white flex items-center gap-2">
                                            {t.name}
                                            {getTournamentTypeBadge(t.priority)}
                                        </h3>
                                        <div className="text-xs text-slate-500 mt-1 flex flex-wrap gap-4 font-medium uppercase tracking-wide">
                                            <span className="flex items-center gap-1.5"><Calendar className="w-3.5 h-3.5 text-slate-400" /> {t.start_date} — {t.last_activity}</span>
                                            <span className="flex items-center gap-1.5"><Activity className="w-3.5 h-3.5 text-slate-400" /> {t.match_count} matches</span>
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <span className="text-xs bg-emerald-500/10 text-emerald-400 px-3 py-1 rounded-full border border-emerald-500/20 uppercase font-bold tracking-wider flex items-center gap-1.5">
                                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span> Active
                                        </span>
                                    </div>
                                </div>

                                <div className="overflow-x-auto">
                                    <table className="w-full text-sm text-left border-collapse">
                                        <thead className="text-xs text-slate-500 uppercase bg-slate-950/50 sticky top-0 backdrop-blur-sm border-b border-slate-800/50">
                                            <tr>
                                                <th className="px-6 py-3 font-semibold tracking-wider w-[120px]">Date</th>
                                                <th className="px-6 py-3 font-semibold tracking-wider">Matchup</th>
                                                <th className="px-6 py-3 font-semibold tracking-wider text-right w-[100px]">Score</th>
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y divide-slate-800/50">
                                            {t.matches.map(m => (
                                                <tr key={m.match_id} className="hover:bg-slate-800/40 transition-colors group">
                                                    <td className="px-6 py-3 text-slate-400 text-xs whitespace-nowrap font-mono">{m.date.split('T')[0]}</td>
                                                    <td className="px-6 py-3">
                                                        <div className="flex flex-col gap-1.5 max-w-md">
                                                            {/* Winner */}
                                                            <div className="flex justify-between items-center group-hover:translate-x-1 transition-transform duration-200">
                                                                <div className="flex items-center gap-2 truncate">
                                                                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500/50"></span>
                                                                    <button
                                                                        onClick={() => onPlayerClick && onPlayerClick({ player_id: m.winner_id, name: m.winner })}
                                                                        className="font-bold text-emerald-400 hover:text-emerald-300 hover:underline truncate text-sm cursor-pointer text-left"
                                                                        title={m.winner}
                                                                    >
                                                                        {m.winner}
                                                                    </button>
                                                                </div>
                                                                <span className="text-[10px] text-slate-600 font-mono bg-slate-950 px-1.5 rounded border border-slate-800 ml-2 shadow-sm min-w-[36px] text-center">{m.winner_utr?.toFixed(2) || '-'}</span>
                                                            </div>
                                                            {/* Loser */}
                                                            <div className="flex justify-between items-center group-hover:translate-x-1 transition-transform duration-200 delay-75">
                                                                <div className="flex items-center gap-2 truncate">
                                                                    <span className="w-1.5 h-1.5 rounded-full bg-rose-500/30"></span>
                                                                    <button
                                                                        onClick={() => onPlayerClick && onPlayerClick({ player_id: m.loser_id, name: m.loser })}
                                                                        className="text-slate-400 hover:text-slate-300 hover:underline truncate text-sm cursor-pointer text-left"
                                                                        title={m.loser}
                                                                    >
                                                                        {m.loser}
                                                                    </button>
                                                                </div>
                                                                <span className="text-[10px] text-slate-700 font-mono bg-slate-950 px-1.5 rounded border border-slate-900 ml-2 min-w-[36px] text-center">{m.loser_utr?.toFixed(2) || '-'}</span>
                                                            </div>
                                                        </div>
                                                    </td>
                                                    <td className="px-6 py-3 text-right font-mono text-slate-300 text-xs font-medium tracking-tight whitespace-nowrap">{m.score}</td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                    {t.matches.length >= 20 && (
                                        <div className="bg-slate-950/30 text-center py-2 text-xs text-slate-500 italic border-t border-slate-800/50">
                                            Showing recent matches
                                        </div>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
};

export default OngoingTournamentsView;
