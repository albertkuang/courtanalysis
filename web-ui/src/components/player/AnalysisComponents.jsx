import React, { useState, useMemo } from 'react';
import { Cpu, Users, Calendar, MapPin } from 'lucide-react';

const AdvancedAnalysis = ({ data, onPlayerClick }) => {
    if (!data) return null;
    const { clutch_score, form_rating, age_analysis } = data;

    return (
        <div className="bg-slate-950 rounded-xl border border-slate-800 p-4">
            <div className="flex items-center gap-2 mb-4">
                <Cpu className="w-4 h-4 text-tennis-blue" />
                <h3 className="text-sm font-semibold text-white uppercase tracking-wider">Advanced Analysis</h3>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-slate-900/50 p-3 rounded-lg border border-slate-800 flex flex-col items-center">
                    <div className="text-xs text-slate-400 uppercase font-bold mb-1">Clutch Score</div>
                    <div className={`text-2xl font-mono font-bold ${!clutch_score ? 'text-slate-600' : clutch_score >= 70 ? 'text-emerald-400' : clutch_score >= 50 ? 'text-amber-400' : 'text-rose-400'}`}>
                        {clutch_score !== null ? clutch_score : 'N/A'}
                    </div>
                    <div className="text-[10px] text-slate-500 mt-1 text-center">Tiebreak & 3-Set Performance</div>
                </div>

                <div className="bg-slate-900/50 p-3 rounded-lg border border-slate-800 flex flex-col items-center">
                    <div className="text-xs text-slate-400 uppercase font-bold mb-1">Form Rating</div>
                    <div className={`text-2xl font-mono font-bold ${!form_rating ? 'text-slate-600' : form_rating >= 60 ? 'text-emerald-400' : 'text-slate-200'}`}>
                        {form_rating !== null ? form_rating : 'N/A'}
                    </div>
                    <div className="text-[10px] text-slate-500 mt-1 text-center">Last 5 Matches Weighted</div>
                </div>

                <div className="bg-slate-900/50 p-3 rounded-lg border border-slate-800 flex flex-col items-center">
                    <div className="text-xs text-slate-400 uppercase font-bold mb-1">Age Cohort</div>
                    {age_analysis ? (
                        <>
                            <div className="text-2xl font-mono font-bold text-tennis-blue">
                                Top {100 - age_analysis.percentile}%
                            </div>
                            <div className="text-[10px] text-slate-500 mt-1 text-center">
                                Avg: {age_analysis.cohort_avg?.toFixed(2)} | Max: {age_analysis.cohort_max?.toFixed(2)}
                            </div>
                        </>
                    ) : (
                        <div className="text-sm text-slate-600 py-2">Insufficient Data</div>
                    )}
                </div>
            </div>

            {data.advanced_metrics && (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
                    <div className="bg-slate-900/50 p-3 rounded-lg border border-slate-800 flex flex-col items-center">
                        <div className="text-xs text-slate-400 uppercase font-bold mb-1">Upset Potential</div>
                        {data.advanced_metrics.upset_rate !== null ? (
                            <>
                                <div className={`text-2xl font-mono font-bold ${data.advanced_metrics.upset_rate > 30 ? 'text-emerald-400' : 'text-slate-300'}`}>
                                    {data.advanced_metrics.upset_rate}%
                                </div>
                                <div className="text-[10px] text-slate-500 mt-1 text-center">
                                    {data.advanced_metrics.upset_wins}/{data.advanced_metrics.upset_opportunities} vs Higher Rated
                                </div>
                            </>
                        ) : (<div className="text-sm text-slate-600 py-2">No Data</div>)}
                    </div>

                    <div className="bg-slate-900/50 p-3 rounded-lg border border-slate-800 flex flex-col items-center">
                        <div className="text-xs text-slate-400 uppercase font-bold mb-1">Bounce Back</div>
                        {data.advanced_metrics.bounce_back_rate !== null ? (
                            <>
                                <div className={`text-2xl font-mono font-bold ${data.advanced_metrics.bounce_back_rate > 60 ? 'text-emerald-400' : data.advanced_metrics.bounce_back_rate < 40 ? 'text-rose-400' : 'text-slate-300'}`}>
                                    {data.advanced_metrics.bounce_back_rate}%
                                </div>
                                <div className="text-[10px] text-slate-500 mt-1 text-center">Win Rate After Loss</div>
                            </>
                        ) : (<div className="text-sm text-slate-600 py-2">No Data</div>)}
                    </div>

                    <div className="bg-slate-900/50 p-3 rounded-lg border border-slate-800 flex flex-col items-center">
                        <div className="text-xs text-slate-400 uppercase font-bold mb-1">Consistency</div>
                        <div className="text-2xl font-mono font-bold text-tennis-blue">
                            {data.advanced_metrics.matches_per_month}
                        </div>
                        <div className="text-[10px] text-slate-500 mt-1 text-center">Matches / Month</div>
                    </div>
                </div>
            )}

            {data.similar_players && data.similar_players.length > 0 && (
                <div className="mt-4 pt-4 border-t border-slate-800">
                    <div className="flex items-center gap-2 mb-3">
                        <Users className="w-3 h-3 text-slate-400" />
                        <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Similar Players</h4>
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-5 gap-2">
                        {data.similar_players.map(p => (
                            <div
                                key={p.player_id}
                                onClick={() => onPlayerClick(p)}
                                className="bg-slate-900 hover:bg-slate-800 p-2 rounded cursor-pointer border border-slate-800 transition-colors flex flex-col"
                            >
                                <div className="text-xs font-bold text-white truncate">{p.name}</div>
                                <div className="flex justify-between items-center mt-1">
                                    <span className="text-[10px] text-slate-500">{p.age} yrs</span>
                                    <span className="text-xs font-mono font-bold text-tennis-green">{p.utr_singles?.toFixed(2)}</span>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
};

const HeadToHeadSection = ({ matches, playerId }) => {
    const [opponentId, setOpponentId] = useState('');

    const opponents = useMemo(() => {
        if (!matches) return [];
        const map = new Map();
        matches.forEach(m => {
            const isWinner = String(m.winner_id) === String(playerId);
            const oppId = isWinner ? m.loser_id : m.winner_id;
            const oppName = isWinner ? m.loser_name : m.winner_name;
            if (oppId && !map.has(oppId)) {
                map.set(oppId, oppName);
            }
        });
        return Array.from(map.entries()).sort((a, b) => a[1].localeCompare(b[1]));
    }, [matches, playerId]);

    const h2hStats = useMemo(() => {
        if (!opponentId || !matches) return null;
        const relevant = matches.filter(m =>
            String(m.winner_id) === String(opponentId) || String(m.loser_id) === String(opponentId)
        );
        const wins = relevant.filter(m => String(m.winner_id) === String(playerId)).length;
        return { matches: relevant, wins, total: relevant.length };
    }, [opponentId, matches, playerId]);

    if (opponents.length === 0) return null;

    return (
        <div className="bg-slate-950 rounded-xl border border-slate-800 p-4">
            <div className="flex items-center gap-2 mb-3">
                <Users className="w-4 h-4 text-tennis-blue" />
                <h3 className="text-sm font-semibold text-white uppercase tracking-wider">Head to Head</h3>
            </div>

            <select
                value={opponentId}
                onChange={(e) => setOpponentId(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white mb-4 focus:outline-none focus:border-tennis-blue"
            >
                <option value="">Select Opponent ({opponents.length})</option>
                {opponents.map(([id, name]) => (
                    <option key={id} value={id}>{name}</option>
                ))}
            </select>

            {h2hStats && (
                <div className="animate-in fade-in slide-in-from-top-2 duration-300">
                    <div className="flex items-center justify-between bg-slate-900 p-3 rounded-lg mb-3 border border-slate-800">
                        <div className="text-center">
                            <div className="text-2xl font-bold text-tennis-green">{h2hStats.wins}</div>
                            <div className="text-[10px] text-slate-500 uppercase">Wins</div>
                        </div>
                        <div className="text-sm font-bold text-slate-400">vs</div>
                        <div className="text-center">
                            <div className="text-2xl font-bold text-rose-400">{h2hStats.total - h2hStats.wins}</div>
                            <div className="text-[10px] text-slate-500 uppercase">Losses</div>
                        </div>
                    </div>

                    <div className="space-y-2 max-h-40 overflow-y-auto pr-1">
                        {h2hStats.matches.map(m => {
                            const isWin = String(m.winner_id) === String(playerId);
                            return (
                                <div key={m.match_id} className="text-xs flex flex-col gap-1 p-2 bg-slate-900/50 rounded border border-slate-800/50">
                                    <div className="flex justify-between items-center">
                                        <span className={`font-bold ${isWin ? 'text-tennis-green' : 'text-rose-400'}`}>{isWin ? 'W' : 'L'}</span>
                                        <span className="text-slate-400">{m.date.split('T')[0]}</span>
                                        <span className="text-slate-300 font-mono">{m.score}</span>
                                    </div>
                                    {m.tournament && (
                                        <div className="flex items-center gap-1 text-[10px] text-slate-500 truncate border-t border-slate-800/50 pt-1 leading-tight">
                                            <MapPin className="w-3 h-3 text-slate-600 shrink-0" /> <span className="truncate">{m.tournament}</span>
                                        </div>
                                    )}
                                </div>
                            )
                        })}
                    </div>
                </div>
            )}
        </div>
    );
};

const MatchLog = ({ matches, playerId, onPlayerClick }) => (
    <div>
        <h3 className="text-sm font-semibold text-white uppercase tracking-wider mb-4 flex items-center gap-2">
            <Calendar className="w-4 h-4 text-tennis-green" /> Recent Matches ({matches?.length || 0})
        </h3>
        <div className="space-y-3">
            {matches && matches.slice(0, 100).map((m) => {
                const isWinner = String(m.winner_id) === String(playerId);
                const opponentId = isWinner ? m.loser_id : m.winner_id;
                const opponentName = isWinner ? m.loser_name : m.winner_name;

                return (
                    <div key={m.match_id} className="bg-slate-800/50 p-3 rounded-lg border border-slate-800 hover:border-slate-600 transition-colors">
                        <div className="flex justify-between items-center mb-1">
                            <span className={`text-xs font-bold px-1.5 py-0.5 rounded ${isWinner ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'}`}>
                                {isWinner ? 'W' : 'L'}
                            </span>
                            <span className="text-xs text-slate-500">{m.date?.split('T')[0]}</span>
                        </div>
                        <div className="text-sm font-medium text-slate-200 truncate flex items-center gap-1">
                            <span className="text-slate-500">vs</span>
                            <button
                                onClick={(e) => {
                                    e.stopPropagation();
                                    if (onPlayerClick) onPlayerClick({ player_id: opponentId, name: opponentName });
                                }}
                                className="hover:text-tennis-blue hover:underline cursor-pointer focus:outline-none text-left truncate"
                                title="View Opponent Profile"
                            >
                                {opponentName}
                            </button>
                        </div>
                        {m.tournament && (
                            <div className="text-[10px] text-slate-500 truncate mt-0.5 flex items-center gap-1">
                                <MapPin className="w-3 h-3 text-slate-600" /> {m.tournament}
                            </div>
                        )}
                        <div className="text-xs text-slate-400 mt-1 flex justify-between">
                            <span>{m.score}</span>
                            <span className="font-mono text-slate-500">{(isWinner ? m.loser_utr : m.winner_utr)?.toFixed(2)}</span>
                        </div>
                    </div>
                )
            })}
        </div>
    </div>
);

export { AdvancedAnalysis, HeadToHeadSection, MatchLog };
