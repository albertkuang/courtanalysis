import React, { useState, useEffect, useMemo } from 'react';
import axios from 'axios';
import {
    Calendar, Loader2, RefreshCw, Search, Filter,
    TrendingUp, ChevronRight, Trophy, MapPin, Clock
} from 'lucide-react';

const RecentMatchesView = ({ onPlayerClick, country, gender, category }) => {
    const [matches, setMatches] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [days, setDays] = useState(10);
    const [searchTerm, setSearchTerm] = useState('');
    const [tournamentLevel, setTournamentLevel] = useState('ALL'); // 'ALL', 'JUNIOR', 'PRO'

    useEffect(() => {
        fetchRecentMatches();
    }, [days, country, gender, category, tournamentLevel]);

    const fetchRecentMatches = async () => {
        setLoading(true);
        setError(null);
        try {
            const params = { days };
            if (country && country !== 'ALL') params.country = country;
            if (gender) params.gender = gender;
            if (category) params.category = category;
            // The API doesn't support 'level' filtering yet, so we filter locally for now 
            // OR we pass it if we update the API. 
            // Given the user request, filtering locally is safer unless we check the API code.
            // Let's check if we can filter locally first.

            const res = await axios.get('/api/matches/recent', { params });
            let data = res.data.data || [];

            if (tournamentLevel === 'JUNIOR') {
                data = data.filter(m => {
                    const t = (m.tournament || '').toUpperCase();
                    return t.includes('JUNIOR') || t.includes('J100') || t.includes('J200') || t.includes('J300') || t.includes('J500') || t.includes('JA') || t.includes('J30') || t.includes('J60');
                });
            } else if (tournamentLevel === 'PRO') {
                data = data.filter(m => {
                    const t = (m.tournament || '').toUpperCase();
                    return !t.includes('JUNIOR') && !t.includes('J30') && !t.includes('J60') && !t.includes('J100') && !t.includes('J200');
                });
            }

            setMatches(data);
        } catch (err) {
            console.error('Error fetching recent matches:', err);
            setError('Failed to load recent matches. Make sure the backend is running.');
        }
        setLoading(false);
    };

    const filtered = useMemo(() => {
        if (!searchTerm) return matches;
        const term = searchTerm.toLowerCase();
        return matches.filter(m =>
            m.winner_name?.toLowerCase().includes(term) ||
            m.loser_name?.toLowerCase().includes(term) ||
            m.tournament?.toLowerCase().includes(term)
        );
    }, [matches, searchTerm]);

    // Group matches by date
    const groupedByDate = useMemo(() => {
        const groups = {};
        filtered.forEach(m => {
            const date = m.date || 'Unknown';
            if (!groups[date]) groups[date] = [];
            groups[date].push(m);
        });
        return Object.entries(groups).sort((a, b) => b[0].localeCompare(a[0]));
    }, [filtered]);

    return (
        <div className="h-full flex flex-col animate-in fade-in duration-300">
            {/* Header */}
            <div className="p-4 md:p-6 border-b border-slate-800 bg-slate-900/50 backdrop-blur shrink-0">
                <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-3">
                        <Calendar className="w-6 h-6 text-tennis-blue" />
                        <div>
                            <h1 className="text-xl font-bold text-white">Recent Matches</h1>
                            <p className="text-xs text-slate-500 mt-0.5">
                                {matches.length} matches in the last {days} days
                            </p>
                        </div>
                    </div>
                    <button
                        onClick={fetchRecentMatches}
                        disabled={loading}
                        className="flex items-center gap-2 px-3 py-2 bg-tennis-blue/10 text-tennis-blue rounded-lg hover:bg-tennis-blue/20 transition-colors disabled:opacity-50 text-sm"
                    >
                        <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                        Refresh
                    </button>
                </div>

                {/* Filters Row */}
                <div className="flex flex-col md:flex-row gap-3">
                    <div className="relative flex-1">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                        <input
                            type="text"
                            placeholder="Search players or tournaments..."
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                            className="w-full bg-slate-800 border border-slate-700 rounded-lg pl-10 pr-3 py-2 text-sm text-white placeholder-slate-400 focus:outline-none focus:border-tennis-blue"
                        />
                    </div>

                    <div className="flex gap-2">
                        <select
                            value={tournamentLevel}
                            onChange={(e) => setTournamentLevel(e.target.value)}
                            className="flex-1 md:flex-none bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-tennis-blue"
                        >
                            <option value="ALL">All Levels</option>
                            <option value="JUNIOR">Junior</option>
                            <option value="PRO">Pro</option>
                        </select>

                        <select
                            value={days}
                            onChange={(e) => setDays(Number(e.target.value))}
                            className="flex-1 md:flex-none bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-tennis-blue"
                        >
                            <option value={3}>Last 3 days</option>
                            <option value={7}>Last 7 days</option>
                            <option value={10}>Last 10 days</option>
                            <option value={30}>Last 30 days</option>
                        </select>
                    </div>
                </div>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-4 md:p-6">
                {loading ? (
                    <div className="flex flex-col items-center justify-center h-64">
                        <Loader2 className="w-8 h-8 text-tennis-blue animate-spin" />
                        <span className="mt-3 text-slate-400 text-sm">Loading recent matches...</span>
                    </div>
                ) : error ? (
                    <div className="bg-rose-500/10 border border-rose-500/30 rounded-lg p-6 text-center">
                        <p className="text-rose-400">{error}</p>
                        <button onClick={fetchRecentMatches} className="mt-3 text-sm text-tennis-blue hover:underline">
                            Try again
                        </button>
                    </div>
                ) : groupedByDate.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-64 text-slate-500">
                        <Calendar className="w-12 h-12 mb-4 opacity-20" />
                        <p>No recent matches found</p>
                        <p className="text-sm mt-1">Try adjusting your filters</p>
                    </div>
                ) : (
                    <div className="space-y-6">
                        {groupedByDate.map(([date, dateMatches]) => (
                            <div key={date}>
                                <div className="flex items-center gap-2 mb-3">
                                    <Clock className="w-4 h-4 text-slate-500" />
                                    <h3 className="text-sm font-semibold text-slate-400">{date}</h3>
                                    <span className="text-xs bg-slate-800 px-2 py-0.5 rounded-full text-slate-500">
                                        {dateMatches.length}
                                    </span>
                                </div>
                                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                    {dateMatches.map((match, idx) => {
                                        const isUpset = match.winner_utr && match.loser_utr && match.winner_utr < match.loser_utr;
                                        return (
                                            <div
                                                key={match.match_id || idx}
                                                className="bg-slate-900 border border-slate-800 rounded-xl p-4 hover:border-slate-600 transition-all"
                                            >
                                                <div className="flex items-center justify-between">
                                                    {/* Tournament */}
                                                    <div className="flex items-center gap-2 text-xs text-slate-500">
                                                        <Trophy className="w-3 h-3" />
                                                        <span className="truncate max-w-[200px]">{match.tournament || 'Unknown'}</span>
                                                        {match.round && <span className="bg-slate-800 px-1.5 py-0.5 rounded text-slate-400">{match.round}</span>}
                                                    </div>
                                                    {isUpset && (
                                                        <span className="text-[10px] uppercase font-bold bg-amber-500/20 text-amber-400 px-2 py-0.5 rounded-full">
                                                            Upset
                                                        </span>
                                                    )}
                                                </div>

                                                {/* Players */}
                                                <div className="mt-3 space-y-1.5">
                                                    <div className="flex items-center justify-between group">
                                                        <div className="flex items-center gap-2">
                                                            <span className="w-5 h-5 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center text-[10px] font-bold">W</span>
                                                            <span
                                                                className="text-white font-medium cursor-pointer hover:text-tennis-blue transition-colors"
                                                                onClick={() => onPlayerClick && onPlayerClick({ player_id: match.winner_id, name: match.winner_name })}
                                                            >
                                                                {match.winner_name}
                                                            </span>
                                                        </div>
                                                        <span className="text-emerald-400 font-mono text-sm">{match.winner_utr ? match.winner_utr.toFixed(2) : '-'}</span>
                                                    </div>
                                                    <div className="flex items-center justify-between">
                                                        <div className="flex items-center gap-2">
                                                            <span className="w-5 h-5 rounded-full bg-slate-700 text-slate-400 flex items-center justify-center text-[10px] font-bold">L</span>
                                                            <span
                                                                className="text-slate-400 cursor-pointer hover:text-tennis-blue transition-colors"
                                                                onClick={() => onPlayerClick && onPlayerClick({ player_id: match.loser_id, name: match.loser_name })}
                                                            >
                                                                {match.loser_name}
                                                            </span>
                                                        </div>
                                                        <span className="text-slate-500 font-mono text-sm">{match.loser_utr ? match.loser_utr.toFixed(2) : '-'}</span>
                                                    </div>
                                                </div>

                                                {/* Score */}
                                                {match.score && (
                                                    <div className="mt-2 pt-2 border-t border-slate-800/50 text-sm text-amber-400 font-medium">
                                                        {match.score}
                                                    </div>
                                                )}
                                            </div>
                                        );
                                    })}
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
};

export default RecentMatchesView;
