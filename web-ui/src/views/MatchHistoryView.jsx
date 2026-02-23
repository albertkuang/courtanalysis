import React, { useState, useMemo, useEffect } from 'react';
import { ClipboardList, Activity, ChevronDown, ChevronLeft, ChevronRight } from 'lucide-react';

// Full Match History View with Year Filter and Match Stats
const MatchHistoryView = ({ matches, playerId, onPlayerClick, pagination, onPageChange, onYearChange }) => {
    const [selectedYear, setSelectedYear] = useState(pagination?.year || 'all');
    const [selectedSurface, setSelectedSurface] = useState('all');
    const [expandedMatch, setExpandedMatch] = useState(null);

    // Sync selectedYear with pagination when it changes
    useEffect(() => {
        if (pagination?.year) {
            setSelectedYear(pagination.year);
        } else if (!pagination?.year && selectedYear !== 'all') {
            // Reset to 'all' if year is cleared
            setSelectedYear('all');
        }
    }, [pagination?.year]);

    const surfaceColors = {
        'Hard': { bg: 'bg-blue-500/20', text: 'text-blue-400', border: 'border-blue-500/40' },
        'Clay': { bg: 'bg-orange-500/20', text: 'text-orange-400', border: 'border-orange-500/40' },
        'Grass': { bg: 'bg-green-500/20', text: 'text-green-400', border: 'border-green-500/40' },
        'Carpet': { bg: 'bg-purple-500/20', text: 'text-purple-400', border: 'border-purple-500/40' },
    };

    const years = useMemo(() => {
        // Use available years from server if provided, otherwise extract from matches
        if (pagination?.availableYears && pagination.availableYears.length > 0) {
            return pagination.availableYears;
        }
        if (!matches || matches.length === 0) return [];
        const uniqueYears = [...new Set(matches.map(m => {
            const date = m.date?.split('T')[0];
            return date ? date.substring(0, 4) : null;
        }).filter(Boolean))];
        return uniqueYears.sort((a, b) => b - a);
    }, [matches, pagination?.availableYears]);

    // Handle year selection
    const handleYearChange = (year) => {
        const newYear = year === 'all' ? null : year;
        setSelectedYear(year);
        if (onYearChange) {
            onYearChange(newYear);
        }
    };

    // Calculate pagination
    const totalPages = pagination?.total ? Math.ceil(pagination.total / pagination.limit) : 1;
    const currentPage = pagination?.offset ? Math.floor(pagination.offset / pagination.limit) + 1 : 1;
    const hasNextPage = pagination && (pagination.offset + pagination.limit < pagination.total);
    const hasPrevPage = pagination && pagination.offset > 0;

    const surfaces = useMemo(() => {
        if (!matches || matches.length === 0) return [];
        return [...new Set(matches.map(m => m.surface).filter(Boolean))].sort();
    }, [matches]);

    const filteredMatches = useMemo(() => {
        if (!matches) return [];
        return matches.filter(m => {
            const date = m.date?.split('T')[0];
            const yearMatch = selectedYear === 'all' || (date && date.startsWith(selectedYear));
            const surfaceMatch = selectedSurface === 'all' || m.surface === selectedSurface;
            return yearMatch && surfaceMatch;
        });
    }, [matches, selectedYear, selectedSurface]);

    const stats = useMemo(() => {
        // Use server-provided aggregated stats if available (covers all pages)
        if (pagination?.stats && (pagination.stats.wins > 0 || pagination.stats.losses > 0)) {
            return pagination.stats;
        }

        if (!filteredMatches || filteredMatches.length === 0) return { wins: 0, losses: 0, winPct: 0, totalAces: 0, totalDfs: 0 };
        const wins = filteredMatches.filter(m => String(m.winner_id) === String(playerId)).length;
        const losses = filteredMatches.length - wins;
        const winPct = filteredMatches.length > 0 ? Math.round((wins / filteredMatches.length) * 100) : 0;
        let totalAces = 0, totalDfs = 0;
        filteredMatches.forEach(m => {
            const isWinner = String(m.winner_id) === String(playerId);
            totalAces += (isWinner ? m.w_ace : m.l_ace) || 0;
            totalDfs += (isWinner ? m.w_df : m.l_df) || 0;
        });
        return { wins, losses, winPct, totalAces, totalDfs };
    }, [filteredMatches, playerId, pagination?.stats]);

    const formatPct = (won, total) => {
        if (!total || total === 0) return '-';
        return Math.round((won / total) * 100) + '%';
    };

    if (!matches || matches.length === 0) {
        return (
            <div className="flex flex-col items-center justify-center p-12 border-2 border-dashed border-slate-800 rounded-2xl bg-slate-900/30">
                <ClipboardList className="w-12 h-12 text-slate-600 mb-4" />
                <h3 className="text-lg font-bold text-slate-400">No Match History</h3>
                <p className="text-slate-500 text-sm mt-2">No recorded matches found for this player.</p>
            </div>
        );
    }

    return (
        <div className="space-y-6 animate-in fade-in duration-300">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-slate-900 p-4 rounded-xl border border-slate-800">
                <div>
                    <h3 className="text-lg font-bold text-white flex items-center gap-2">
                        <ClipboardList className="w-5 h-5 text-tennis-blue" />
                        Full Match History
                    </h3>
                    <p className="text-sm text-slate-400 mt-1">
                        {pagination?.total ? `${pagination.total} matches` : `${matches.length} matches`}
                        {selectedYear !== 'all' ? `in ${selectedYear}` : ''} {selectedSurface !== 'all' ? `on ${selectedSurface}` : ''}
                    </p>
                </div>
                <div className="flex gap-2 flex-wrap">
                    <div className="relative">
                        <select value={selectedYear} onChange={(e) => handleYearChange(e.target.value)}
                            className="appearance-none bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 pr-10 text-white text-sm font-medium cursor-pointer hover:border-slate-600 focus:outline-none focus:border-tennis-blue transition-colors">
                            <option value="all">All Years</option>
                            {years.map(year => (<option key={year} value={year}>{year}</option>))}
                        </select>
                        <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
                    </div>
                    {surfaces.length > 0 && (
                        <div className="relative">
                            <select value={selectedSurface} onChange={(e) => setSelectedSurface(e.target.value)}
                                className="appearance-none bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 pr-10 text-white text-sm font-medium cursor-pointer hover:border-slate-600 focus:outline-none focus:border-tennis-blue transition-colors">
                                <option value="all">All Surfaces</option>
                                <option value="Hard">Hard</option>
                                <option value="Clay">Clay</option>
                                <option value="Grass">Grass</option>
                                <option value="Carpet">Carpet</option>
                            </select>
                            <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
                        </div>
                    )}
                </div>
            </div>

            <div className="grid grid-cols-3 sm:grid-cols-5 gap-4">
                <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-xl p-4 text-center">
                    <div className="text-3xl font-bold text-emerald-400 font-mono">{stats.wins}</div>
                    <div className="text-xs text-emerald-400/70 uppercase font-semibold mt-1">Wins</div>
                </div>
                <div className="bg-rose-500/10 border border-rose-500/30 rounded-xl p-4 text-center">
                    <div className="text-3xl font-bold text-rose-400 font-mono">{stats.losses}</div>
                    <div className="text-xs text-rose-400/70 uppercase font-semibold mt-1">Losses</div>
                </div>
                <div className="bg-slate-800 border border-slate-700 rounded-xl p-4 text-center">
                    <div className={`text-3xl font-bold font-mono ${stats.winPct >= 50 ? 'text-emerald-400' : 'text-rose-400'}`}>{stats.winPct}%</div>
                    <div className="text-xs text-slate-400 uppercase font-semibold mt-1">Win Rate</div>
                </div>
                <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-3 text-center hidden sm:block">
                    <div className="text-2xl font-bold text-amber-400 font-mono">{stats.totalAces}</div>
                    <div className="text-xs text-amber-400/70 uppercase font-semibold mt-1">Aces</div>
                </div>
                <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-3 text-center hidden sm:block">
                    <div className="text-2xl font-bold text-red-400 font-mono">{stats.totalDfs}</div>
                    <div className="text-xs text-red-400/70 uppercase font-semibold mt-1">DFs</div>
                </div>
            </div>

            <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-xl">
                <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                        <thead className="bg-slate-950 text-slate-400 uppercase text-xs font-semibold tracking-wider">
                            <tr>
                                <th className="px-4 py-3 text-left">Date</th>
                                <th className="px-4 py-3 text-center">Result</th>
                                <th className="px-4 py-3 text-left">Opponent</th>
                                <th className="px-4 py-3 text-center">Score</th>
                                <th className="px-2 py-3 text-center hidden lg:table-cell">Surface</th>
                                <th className="px-2 py-3 text-center hidden md:table-cell" title="Aces">🎾</th>
                                <th className="px-2 py-3 text-center hidden md:table-cell" title="Double Faults">❌</th>
                                <th className="px-4 py-3 text-left hidden xl:table-cell">Tournament</th>
                                <th className="px-2 py-3 text-center hidden sm:table-cell">Opp UTR</th>
                                <th className="px-2 py-3 text-center">Stats</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800">
                            {filteredMatches.map((m) => {
                                const isWinner = String(m.winner_id) === String(playerId);
                                const opponentId = isWinner ? m.loser_id : m.winner_id;
                                const opponentName = isWinner ? m.loser_name : m.winner_name;
                                const opponentUtr = isWinner ? m.loser_utr : m.winner_utr;
                                const playerAces = isWinner ? m.w_ace : m.l_ace;
                                const playerDfs = isWinner ? m.w_df : m.l_df;
                                const hasStats = playerAces != null || m.minutes != null;
                                const surfaceStyle = surfaceColors[m.surface] || { bg: 'bg-slate-700', text: 'text-slate-300', border: 'border-slate-600' };
                                const isExpanded = expandedMatch === m.match_id;

                                return (
                                    <React.Fragment key={m.match_id}>
                                        <tr className={`hover:bg-slate-800/50 transition-colors ${isExpanded ? 'bg-slate-800/30' : ''}`}>
                                            <td className="px-4 py-3 text-slate-300 font-mono text-xs">{m.date?.split('T')[0]}</td>
                                            <td className="px-4 py-3 text-center">
                                                <span className={`px-2 py-1 rounded text-xs font-bold ${isWinner ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'}`}>
                                                    {isWinner ? 'WIN' : 'LOSS'}
                                                </span>
                                            </td>
                                            <td className="px-4 py-3">
                                                <button onClick={() => onPlayerClick && onPlayerClick({ player_id: opponentId, name: opponentName })}
                                                    className="text-slate-200 hover:text-tennis-blue hover:underline font-medium transition-colors text-left truncate max-w-[150px] block" title={opponentName}>
                                                    {opponentName || 'Unknown'}
                                                </button>
                                            </td>
                                            <td className="px-4 py-3 text-center"><span className="font-mono text-slate-300">{m.score || '-'}</span></td>
                                            <td className="px-2 py-3 text-center hidden lg:table-cell">
                                                {m.surface && (<span className={`px-2 py-0.5 rounded text-xs font-semibold ${surfaceStyle.bg} ${surfaceStyle.text} border ${surfaceStyle.border}`}>{m.surface.charAt(0)}</span>)}
                                            </td>
                                            <td className="px-2 py-3 text-center hidden md:table-cell"><span className="font-mono text-amber-400 text-xs">{playerAces ?? '-'}</span></td>
                                            <td className="px-2 py-3 text-center hidden md:table-cell"><span className="font-mono text-red-400 text-xs">{playerDfs ?? '-'}</span></td>
                                            <td className="px-4 py-3 text-slate-500 text-xs truncate max-w-[180px] hidden xl:table-cell" title={m.tournament}>{m.tournament || '-'}</td>
                                            <td className="px-2 py-3 text-center hidden sm:table-cell"><span className="font-mono text-tennis-green text-xs">{opponentUtr?.toFixed(2) || '-'}</span></td>
                                            <td className="px-2 py-3 text-center">
                                                {hasStats ? (
                                                    <button onClick={() => setExpandedMatch(isExpanded ? null : m.match_id)}
                                                        className={`p-1 rounded hover:bg-slate-700 transition-colors ${isExpanded ? 'text-tennis-blue' : 'text-slate-400'}`} title="View match stats">
                                                        <Activity className="w-4 h-4" />
                                                    </button>
                                                ) : (<span className="text-slate-600">-</span>)}
                                            </td>
                                        </tr>
                                        {isExpanded && hasStats && (
                                            <tr className="bg-slate-800/50">
                                                <td colSpan="10" className="px-4 py-4">
                                                    <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
                                                        {m.minutes && (<div className="text-center"><div className="text-lg font-bold text-slate-200 font-mono">{m.minutes}m</div><div className="text-xs text-slate-500">Duration</div></div>)}
                                                        <div className="text-center"><div className="text-lg font-bold text-amber-400 font-mono">{isWinner ? m.w_ace : m.l_ace || 0}</div><div className="text-xs text-slate-500">Your Aces</div></div>
                                                        <div className="text-center"><div className="text-lg font-bold text-red-400 font-mono">{isWinner ? m.w_df : m.l_df || 0}</div><div className="text-xs text-slate-500">Your DFs</div></div>
                                                        <div className="text-center"><div className="text-lg font-bold text-sky-400 font-mono">{formatPct(isWinner ? m.w_1stIn : m.l_1stIn, isWinner ? m.w_svpt : m.l_svpt)}</div><div className="text-xs text-slate-500">1st Serve %</div></div>
                                                        <div className="text-center"><div className="text-lg font-bold text-emerald-400 font-mono">{formatPct(isWinner ? m.w_1stWon : m.l_1stWon, isWinner ? m.w_1stIn : m.l_1stIn)}</div><div className="text-xs text-slate-500">1st Win %</div></div>
                                                        <div className="text-center"><div className="text-lg font-bold text-violet-400 font-mono">{isWinner ? m.w_bpSaved : m.l_bpSaved || 0}/{isWinner ? m.w_bpFaced : m.l_bpFaced || 0}</div><div className="text-xs text-slate-500">BP Saved</div></div>
                                                        <div className="text-center col-span-2 md:col-span-4 lg:col-span-6 mt-2 pt-2 border-t border-slate-700">
                                                            <span className="text-xs text-slate-400 uppercase font-semibold">Opponent: </span>
                                                            <span className="text-slate-300 text-sm">
                                                                {isWinner ? m.l_ace : m.w_ace || 0} aces, {isWinner ? m.l_df : m.w_df || 0} DFs,{' '}
                                                                {formatPct(isWinner ? m.l_1stIn : m.w_1stIn, isWinner ? m.l_svpt : m.w_svpt)} 1st,{' '}
                                                                {isWinner ? m.l_bpSaved : m.w_bpSaved || 0}/{isWinner ? m.l_bpFaced : m.w_bpFaced || 0} BP
                                                            </span>
                                                        </div>
                                                    </div>
                                                </td>
                                            </tr>
                                        )}
                                    </React.Fragment>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
                <div className="bg-slate-950 px-4 py-3 border-t border-slate-800 text-xs text-slate-500 flex justify-between items-center">
                    <span>Showing {matches.length} of {pagination?.total || matches.length} matches</span>

                    {/* Pagination Controls */}
                    {pagination && pagination.total > pagination.limit && (
                        <div className="flex items-center gap-2">
                            <button
                                onClick={() => onPageChange && onPageChange(Math.max(0, pagination.offset - pagination.limit))}
                                disabled={!hasPrevPage}
                                className={`p-1 rounded ${hasPrevPage ? 'hover:bg-slate-700 text-slate-300' : 'text-slate-600 cursor-not-allowed'}`}
                                title="Previous page"
                            >
                                <ChevronLeft className="w-4 h-4" />
                            </button>
                            <span className="text-slate-400">
                                Page {currentPage} of {totalPages}
                            </span>
                            <button
                                onClick={() => onPageChange && onPageChange(pagination.offset + pagination.limit)}
                                disabled={!hasNextPage}
                                className={`p-1 rounded ${hasNextPage ? 'hover:bg-slate-700 text-slate-300' : 'text-slate-600 cursor-not-allowed'}`}
                                title="Next page"
                            >
                                <ChevronRight className="w-4 h-4" />
                            </button>
                        </div>
                    )}

                    {(selectedYear !== 'all' || selectedSurface !== 'all') && (
                        <button onClick={() => { setSelectedYear('all'); setSelectedSurface('all'); if (onYearChange) onYearChange(null); }} className="text-tennis-blue hover:underline">Clear Filters</button>
                    )}
                </div>
            </div>
        </div>
    );
};

export default MatchHistoryView;
