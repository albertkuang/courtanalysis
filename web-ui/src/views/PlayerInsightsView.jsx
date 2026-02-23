import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Loader2, Lightbulb } from 'lucide-react';

const PlayerInsightsView = ({ playerId }) => {
    const [insights, setInsights] = useState([]);
    const [loading, setLoading] = useState(true);
    const [expandedInsight, setExpandedInsight] = useState(null);

    useEffect(() => {
        const fetchInsights = async () => {
            if (!playerId) return;
            setLoading(true);
            try {
                const res = await axios.get(`/api/players/${playerId}/insights?years=5`);
                setInsights(res.data.data || []);
            } catch (err) {
                console.error('Failed to fetch insights:', err);
            }
            setLoading(false);
        };
        fetchInsights();
    }, [playerId]);

    if (loading) {
        return (
            <div className="flex justify-center py-16">
                <Loader2 className="w-8 h-8 animate-spin text-tennis-blue" />
            </div>
        );
    }

    if (!insights || insights.length === 0) {
        return (
            <div className="flex flex-col items-center justify-center p-12 border-2 border-dashed border-slate-800 rounded-2xl bg-slate-900/30">
                <Lightbulb className="w-12 h-12 text-slate-600 mb-4" />
                <h3 className="text-lg font-bold text-slate-400">No Insights Available</h3>
                <p className="text-slate-500 text-sm mt-2 text-center">
                    Not enough match data to generate patterns.<br />
                    Insights require matches from pro-level tournaments.
                </p>
            </div>
        );
    }

    return (
        <div className="space-y-4 animate-in fade-in duration-300">
            <div className="flex items-center gap-2 mb-4">
                <Lightbulb className="w-5 h-5 text-amber-400" />
                <h3 className="text-lg font-bold text-white">Player Insights</h3>
                <span className="text-xs text-slate-500 bg-slate-800 px-2 py-1 rounded">Last 5 years</span>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
                {insights.map((insight, idx) => {
                    const isExpanded = expandedInsight === idx;
                    const winPctColor = insight.win_pct >= 60 ? 'text-emerald-400' : insight.win_pct <= 40 ? 'text-rose-400' : 'text-amber-400';

                    return (
                        <div
                            key={idx}
                            className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden hover:border-slate-700 transition-colors"
                        >
                            <div
                                className="p-4 cursor-pointer"
                                onClick={() => setExpandedInsight(isExpanded ? null : idx)}
                            >
                                <div className="flex items-start justify-between">
                                    <div className="flex items-center gap-3">
                                        <span className="text-2xl">{insight.emoji}</span>
                                        <div>
                                            <div className="font-semibold text-white">{insight.title}</div>
                                            <div className="text-sm text-slate-400">{insight.description}</div>
                                        </div>
                                    </div>
                                    <div className="text-right">
                                        <div className={`text-2xl font-bold font-mono ${winPctColor}`}>
                                            {insight.win_pct}%
                                        </div>
                                        <div className="text-xs text-slate-500">
                                            {insight.wins}W - {insight.losses}L
                                        </div>
                                    </div>
                                </div>

                                <div className="flex gap-1 mt-3 flex-wrap">
                                    {insight.matches?.slice(0, 5).map((m, i) => (
                                        <span
                                            key={i}
                                            className={`w-6 h-6 rounded flex items-center justify-center text-xs font-bold ${m.result === 'W' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'
                                                }`}
                                            title={`${m.result === 'W' ? 'Win' : 'Loss'} vs ${m.opponent}`}
                                        >
                                            {m.result === 'W' ? '✓' : '✗'}
                                        </span>
                                    ))}
                                    {insight.total_matches > 5 && (
                                        <span className="text-xs text-slate-500 self-center ml-1">
                                            +{insight.total_matches - 5} more
                                        </span>
                                    )}
                                </div>
                            </div>

                            {isExpanded && insight.matches && (
                                <div className="border-t border-slate-800 bg-slate-950/50 p-3">
                                    <table className="w-full text-xs">
                                        <thead className="text-slate-500 uppercase">
                                            <tr>
                                                <th className="text-left pb-2"></th>
                                                <th className="text-left pb-2">Opponent</th>
                                                <th className="text-left pb-2 hidden sm:table-cell">Tournament</th>
                                                <th className="text-right pb-2">Date</th>
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y divide-slate-800/50">
                                            {insight.matches.map((m, i) => (
                                                <tr key={i} className="text-slate-300">
                                                    <td className="py-1.5 pr-2">
                                                        <span className={`font-bold ${m.result === 'W' ? 'text-emerald-400' : 'text-rose-400'}`}>
                                                            {m.result === 'W' ? '✓' : '✗'}
                                                        </span>
                                                    </td>
                                                    <td className="py-1.5">
                                                        {m.opponent}
                                                        {m.opponent_age && <span className="text-slate-500 ml-1">({m.opponent_age}yo)</span>}
                                                    </td>
                                                    <td className="py-1.5 text-slate-500 truncate max-w-[150px] hidden sm:table-cell" title={m.tournament}>
                                                        {m.tournament}
                                                    </td>
                                                    <td className="py-1.5 text-right text-slate-500 font-mono">{m.date}</td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>
        </div>
    );
};

export default PlayerInsightsView;
