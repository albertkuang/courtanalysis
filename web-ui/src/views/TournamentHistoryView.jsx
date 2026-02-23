import React, { useState, useEffect, useMemo } from 'react';
import axios from 'axios';
import {
    Trophy, Loader2, RefreshCw, Search, Calendar, MapPin,
    ChevronRight, Filter, Users, Medal
} from 'lucide-react';

const categoryOptions = [
    { value: 'all', label: 'All Events' },
    { value: 'grand_slam', label: 'Grand Slams' },
    { value: 'masters', label: 'Masters / WTA-1000' },
    { value: 'tour', label: 'Tour Events' },
    { value: 'challenger', label: 'Challengers' },
    { value: 'futures', label: 'Futures / ITF' },
];

const genderOptions = [
    { value: 'all', label: 'All' },
    { value: 'M', label: "Men's" },
    { value: 'F', label: "Women's" },
];

const TournamentHistoryView = ({ onPlayerClick }) => {
    const [tournaments, setTournaments] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [category, setCategory] = useState('all');
    const [gender, setGender] = useState('all');
    const [year, setYear] = useState(null);
    const [searchTerm, setSearchTerm] = useState('');
    const [selectedTournament, setSelectedTournament] = useState(null);
    const [drawMatches, setDrawMatches] = useState([]);
    const [drawLoading, setDrawLoading] = useState(false);

    useEffect(() => {
        fetchTournaments();
    }, [category, gender, year]);

    const fetchTournaments = async () => {
        setLoading(true);
        setError(null);
        try {
            const params = { limit: 100 };
            if (category !== 'all') params.category = category;
            if (gender !== 'all') params.gender = gender;
            if (year) params.year = year;
            if (searchTerm) params.search = searchTerm;

            const res = await axios.get('/api/tournaments/history', { params });
            setTournaments(res.data.data || []);
        } catch (err) {
            console.error('Error fetching tournament history:', err);
            setError('Failed to load tournament history.');
        }
        setLoading(false);
    };

    const fetchDraw = async (tournamentName, tournamentYear) => {
        setDrawLoading(true);
        try {
            const params = {};
            if (tournamentYear) params.year = tournamentYear;
            const res = await axios.get(`/api/tournaments/${encodeURIComponent(tournamentName)}/draw`, { params });
            setDrawMatches(res.data.data || []);
        } catch (err) {
            console.error('Error fetching draw:', err);
            setDrawMatches([]);
        }
        setDrawLoading(false);
    };

    const handleTournamentClick = (t) => {
        setSelectedTournament(t);
        fetchDraw(t.tournament_name, t.year);
    };

    const years = useMemo(() => {
        const currentYear = new Date().getFullYear();
        return Array.from({ length: 10 }, (_, i) => currentYear - i);
    }, []);

    const handleSearch = (e) => {
        e.preventDefault();
        fetchTournaments();
    };

    // Round ordering for draw display
    const roundOrder = { 'R128': 1, 'R64': 2, 'R32': 3, 'R16': 4, 'QF': 5, 'SF': 6, 'F': 7 };

    return (
        <div className="h-full flex flex-col animate-in fade-in duration-300">
            {/* Header */}
            <div className="p-4 md:p-6 border-b border-slate-800 bg-slate-900/50 backdrop-blur shrink-0">
                <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-3">
                        <Trophy className="w-6 h-6 text-amber-400" />
                        <div>
                            <h1 className="text-xl font-bold text-white">Tournament History</h1>
                            <p className="text-xs text-slate-500 mt-0.5">Browse historical tournament results and draws</p>
                        </div>
                    </div>
                    <button
                        onClick={fetchTournaments}
                        disabled={loading}
                        className="flex items-center gap-2 px-3 py-2 bg-amber-500/10 text-amber-400 rounded-lg hover:bg-amber-500/20 transition-colors text-sm"
                    >
                        <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                        Refresh
                    </button>
                </div>

                {/* Filters */}
                <div className="flex flex-wrap gap-3">
                    <form onSubmit={handleSearch} className="relative flex-1 min-w-[200px]">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                        <input
                            type="text"
                            placeholder="Search tournaments..."
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                            className="w-full bg-slate-800 border border-slate-700 rounded-lg pl-10 pr-3 py-2 text-sm text-white placeholder-slate-400 focus:outline-none focus:border-amber-500"
                        />
                    </form>

                    <select
                        value={category}
                        onChange={(e) => setCategory(e.target.value)}
                        className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-amber-500"
                    >
                        {categoryOptions.map(opt => (
                            <option key={opt.value} value={opt.value}>{opt.label}</option>
                        ))}
                    </select>

                    <select
                        value={gender}
                        onChange={(e) => setGender(e.target.value)}
                        className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-amber-500"
                    >
                        {genderOptions.map(opt => (
                            <option key={opt.value} value={opt.value}>{opt.label}</option>
                        ))}
                    </select>

                    <select
                        value={year || ''}
                        onChange={(e) => setYear(e.target.value ? Number(e.target.value) : null)}
                        className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-amber-500"
                    >
                        <option value="">All Years</option>
                        {years.map(y => (
                            <option key={y} value={y}>{y}</option>
                        ))}
                    </select>
                </div>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto">
                {loading ? (
                    <div className="flex flex-col items-center justify-center h-64">
                        <Loader2 className="w-8 h-8 text-amber-400 animate-spin" />
                        <span className="mt-3 text-slate-400 text-sm">Loading tournament history...</span>
                    </div>
                ) : error ? (
                    <div className="p-6">
                        <div className="bg-rose-500/10 border border-rose-500/30 rounded-lg p-6 text-center">
                            <p className="text-rose-400">{error}</p>
                        </div>
                    </div>
                ) : (
                    <div className="flex h-full">
                        {/* Tournament List */}
                        <div className={`${selectedTournament ? 'w-1/3 border-r border-slate-800' : 'w-full'} overflow-y-auto p-4`}>
                            {tournaments.length === 0 ? (
                                <div className="flex flex-col items-center justify-center h-64 text-slate-500">
                                    <Trophy className="w-12 h-12 mb-4 opacity-20" />
                                    <p>No tournaments found</p>
                                </div>
                            ) : (
                                <div className="space-y-2">
                                    {tournaments.map((t, idx) => (
                                        <div
                                            key={`${t.tournament_name}-${t.year}-${idx}`}
                                            onClick={() => handleTournamentClick(t)}
                                            className={`bg-slate-900 border rounded-xl p-4 cursor-pointer transition-all ${selectedTournament?.tournament_name === t.tournament_name && selectedTournament?.year === t.year
                                                    ? 'border-amber-500/50 bg-amber-900/10'
                                                    : 'border-slate-800 hover:border-slate-600'
                                                }`}
                                        >
                                            <div className="flex items-center justify-between">
                                                <div>
                                                    <h3 className="font-semibold text-white text-sm">{t.tournament_name}</h3>
                                                    <div className="flex items-center gap-2 mt-1 text-xs text-slate-500">
                                                        <Calendar className="w-3 h-3" />{t.year}
                                                        {t.surface && <><span>•</span><MapPin className="w-3 h-3" />{t.surface}</>}
                                                        {t.level && <span className="bg-slate-800 px-1.5 py-0.5 rounded text-slate-400">{t.level}</span>}
                                                    </div>
                                                </div>
                                                <ChevronRight className="w-4 h-4 text-slate-500" />
                                            </div>
                                            {t.winner_name && (
                                                <div className="mt-2 pt-2 border-t border-slate-800/50 flex items-center gap-2">
                                                    <Medal className="w-3 h-3 text-amber-400" />
                                                    <span className="text-sm text-amber-400 font-medium">{t.winner_name}</span>
                                                    {t.score && <span className="text-xs text-slate-500 ml-auto">{t.score}</span>}
                                                </div>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>

                        {/* Draw Detail */}
                        {selectedTournament && (
                            <div className="flex-1 overflow-y-auto p-4">
                                <div className="mb-4">
                                    <h2 className="text-lg font-bold text-white">
                                        {selectedTournament.tournament_name} {selectedTournament.year}
                                    </h2>
                                    <p className="text-sm text-slate-400">Tournament Draw</p>
                                </div>

                                {drawLoading ? (
                                    <div className="flex items-center justify-center h-32">
                                        <Loader2 className="w-6 h-6 text-amber-400 animate-spin" />
                                    </div>
                                ) : drawMatches.length === 0 ? (
                                    <div className="text-center text-slate-500 py-12">
                                        <Users className="w-8 h-8 mx-auto mb-2 opacity-30" />
                                        <p className="text-sm">No draw data available for this tournament</p>
                                    </div>
                                ) : (
                                    <div className="space-y-2">
                                        {drawMatches
                                            .sort((a, b) => (roundOrder[a.round] || 0) - (roundOrder[b.round] || 0))
                                            .map((match, idx) => (
                                                <div key={idx} className="bg-slate-900 border border-slate-800 rounded-lg p-3">
                                                    <div className="flex items-center gap-2 text-xs text-slate-500 mb-2">
                                                        <span className="bg-slate-800 px-1.5 py-0.5 rounded">{match.round}</span>
                                                        {match.date && <span>{match.date}</span>}
                                                    </div>
                                                    <div className="flex justify-between items-center">
                                                        <div>
                                                            <span
                                                                className="font-medium text-white cursor-pointer hover:text-tennis-blue transition-colors"
                                                                onClick={() => onPlayerClick && onPlayerClick({ player_id: match.winner_id, name: match.winner_name })}
                                                            >
                                                                {match.winner_name}
                                                            </span>
                                                            <span className="text-slate-500 mx-2">def.</span>
                                                            <span
                                                                className="text-slate-400 cursor-pointer hover:text-tennis-blue transition-colors"
                                                                onClick={() => onPlayerClick && onPlayerClick({ player_id: match.loser_id, name: match.loser_name })}
                                                            >
                                                                {match.loser_name}
                                                            </span>
                                                        </div>
                                                        <span className="text-amber-400 font-mono text-sm">{match.score}</span>
                                                    </div>
                                                </div>
                                            ))}
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
};

export default TournamentHistoryView;
