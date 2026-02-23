import React, { useState } from 'react';
import axios from 'axios';
import { Search, GraduationCap, Users, ChevronRight, MapPin, ExternalLink, Loader2, AlertCircle } from 'lucide-react';

const CollegeScout = ({ onPlayerClick }) => {
    const [query, setQuery] = useState('');
    const [results, setResults] = useState([]);
    const [selectedCollege, setSelectedCollege] = useState(null);
    const [roster, setRoster] = useState([]);
    const [loading, setLoading] = useState(false);
    const [searching, setSearching] = useState(false);
    const [error, setError] = useState(null);

    const [gender, setGender] = useState('M'); // 'M' or 'F'
    const [division, setDivision] = useState('D1'); // 'D1', 'D2', 'D3', 'NAIA', 'JUCO'
    const [sortOrder, setSortOrder] = useState('asc'); // 'asc' or 'desc'

    // Reset selection when gender/division changes, and auto-fetch top colleges
    React.useEffect(() => {
        setSelectedCollege(null);
        setRoster([]);
        setResults([]);

        // Auto-fetch list of colleges for this division
        const fetchColleges = async () => {
            setSearching(true);
            try {
                // Search with empty query to get top colleges for division
                const res = await axios.get('/api/college/search', {
                    params: {
                        query: '',
                        gender,
                        division,
                        _t: Date.now()
                    }
                });

                let data = [];
                if (res.data && Array.isArray(res.data.data)) {
                    data = res.data.data;
                } else if (Array.isArray(res.data)) {
                    data = res.data;
                }

                if (Array.isArray(data)) {
                    // Sort alphabetically by name
                    data.sort((a, b) => a.name.localeCompare(b.name));
                    setResults(data);
                }
            } catch (err) {
                console.error("Auto-fetch failed", err);
            }
            setSearching(false);
        };

        fetchColleges();
    }, [gender, division]);

    const handleSearch = async (e) => {
        e.preventDefault();
        setError(null);
        // Allows empty query to refresh list
        // if (!query.trim()) return;

        setSearching(true);
        setSelectedCollege(null); // Clear selection on new search
        try {
            console.log("Searching for:", query);
            // Add cache busting timestamp
            const res = await axios.get('/api/college/search', {
                params: {
                    query,
                    gender,
                    division,
                    _t: Date.now()
                }
            });
            console.log("Search response:", res.data);

            // Handle different response structures gracefully
            let data = [];
            if (res.data && Array.isArray(res.data.data)) {
                data = res.data.data;
            } else if (Array.isArray(res.data)) {
                data = res.data;
            }

            if (Array.isArray(data)) {
                // Sort alphabetically by name
                data.sort((a, b) => a.name.localeCompare(b.name));
                setResults(data);
                if (data.length === 0) {
                    setError("No colleges found matching that name.");
                }
            } else {
                console.error("Unexpected response format:", res.data);
                setError("Received invalid data format from server.");
                setResults([]);
            }

        } catch (err) {
            console.error("Search failed:", err);
            setError(err.response?.data?.detail || err.message || "Search failed. Please try again.");
            setResults([]);
        }
        setSearching(false);
    };

    const handleSelectCollege = async (college) => {
        setSelectedCollege(college);
        setError(null);
        setLoading(true);
        try {
            // Use club_id from search result, also cache bust
            // Use gender-specific club ID if available
            let clubId = college.clubId || college.id;
            if (gender === 'M' && college.mensClubId) clubId = college.mensClubId;
            if (gender === 'F' && college.womensClubId) clubId = college.womensClubId;

            const res = await axios.get(`/api/college/${clubId}/roster`, {
                params: {
                    gender,
                    _t: Date.now()
                }
            });
            const data = res.data.data || [];
            if (Array.isArray(data)) {
                setRoster(data);
            } else {
                console.error("Unexpected roster format:", res.data);
                setError("Invalid roster data received.");
                setRoster([]);
            }
        } catch (err) {
            console.error("Fetch roster failed:", err);
            setError(err.response?.data?.detail || "Failed to fetch roster. Please try again.");
        }
        setLoading(false);
    };

    return (
        <div className="space-y-6 animate-in fade-in duration-500">
            {/* Header */}
            <div className="bg-gradient-to-r from-emerald-900 to-slate-900 rounded-xl p-6 border border-emerald-500/30 shadow-lg">
                <div className="flex items-center gap-3 mb-2">
                    <GraduationCap className="w-8 h-8 text-emerald-400" />
                    <h2 className="text-2xl font-bold text-white">College Scout</h2>
                </div>
                <p className="text-emerald-100/70">
                    Find college programs, explore rosters, and analyze team strength.
                </p>

                {/* Search Inputs */}
                <form onSubmit={handleSearch} className="mt-6 flex flex-col md:flex-row gap-4">
                    {/* Category Dropdown */}
                    <div className="w-full md:w-48">
                        <select
                            value={division}
                            onChange={(e) => setDivision(e.target.value)}
                            className="w-full bg-slate-950/50 border border-emerald-500/30 rounded-lg py-3 px-4 text-white focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 transition-all font-sans"
                        >
                            <option value="D1">NCAA D1</option>
                            <option value="D2">NCAA D2</option>
                            <option value="D3">NCAA D3</option>
                            <option value="NAIA">NAIA</option>
                            <option value="JUCO">JUCO</option>
                        </select>
                    </div>

                    {/* College Name Input */}
                    <div className="relative flex-1">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                        <input
                            type="text"
                            value={query}
                            onChange={(e) => setQuery(e.target.value)}
                            placeholder="College Name (e.g. 'Stanford')"
                            className="w-full bg-slate-950/50 border border-emerald-500/30 rounded-lg py-3 pl-10 pr-4 text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 transition-all font-sans"
                        />
                    </div>

                    {/* Gender Toggle (Integrated or separate?) - Kept separate as requested but functionally linked */}
                    <div className="flex rounded-lg bg-slate-950/50 border border-emerald-500/30 p-1">
                        <button
                            type="button"
                            onClick={() => setGender('M')}
                            className={`px-4 py-2 rounded-md text-sm font-bold transition-all ${gender === 'M' ? 'bg-emerald-600 text-white shadow-lg' : 'text-slate-400 hover:text-white'}`}
                        >
                            Men
                        </button>
                        <button
                            type="button"
                            onClick={() => setGender('F')}
                            className={`px-4 py-2 rounded-md text-sm font-bold transition-all ${gender === 'F' ? 'bg-emerald-600 text-white shadow-lg' : 'text-slate-400 hover:text-white'}`}
                        >
                            Women
                        </button>
                    </div>

                    <button
                        type="submit"
                        disabled={searching}
                        className="bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-2 px-6 rounded-lg transition-colors flex items-center gap-2 disabled:opacity-50 whitespace-nowrap"
                    >
                        {searching ? <Loader2 className="w-5 h-5 animate-spin" /> : 'Search'}
                    </button>
                </form>
            </div>

            {/* Error Display */}
            {error && (
                <div className="bg-red-500/10 border border-red-500/50 text-red-500 p-4 rounded-lg flex items-center gap-2 animate-in fade-in slide-in-from-top-2">
                    <AlertCircle className="w-5 h-5" />
                    <span className="font-bold">Error:</span> {error}
                </div>
            )}

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Results List */}
                {(results.length > 0 || searching) && (
                    <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden h-[600px] flex flex-col shadow-xl">
                        <div className="p-4 border-b border-slate-800 bg-slate-950/50 flex justification-between items-center">
                            <h3 className="font-bold text-white flex items-center gap-2">
                                <Search className="w-4 h-4 text-emerald-400" /> Search Results
                                <span className="bg-slate-800 text-xs px-2 py-0.5 rounded text-slate-400">{results.length}</span>
                            </h3>
                            {/* Sort Controls */}
                            <div className="flex bg-slate-800 rounded p-0.5">
                                <button
                                    onClick={() => setSortOrder('asc')}
                                    className={`px-2 py-0.5 text-xs rounded transition-all ${sortOrder === 'asc' ? 'bg-emerald-600 text-white' : 'text-slate-400 hover:text-white'}`}
                                >
                                    A-Z
                                </button>
                                <button
                                    onClick={() => setSortOrder('desc')}
                                    className={`px-2 py-0.5 text-xs rounded transition-all ${sortOrder === 'desc' ? 'bg-emerald-600 text-white' : 'text-slate-400 hover:text-white'}`}
                                >
                                    Z-A
                                </button>
                            </div>
                        </div>

                        <div className="overflow-y-auto flex-1 p-2 space-y-2">
                            {[...results]
                                .sort((a, b) => sortOrder === 'asc'
                                    ? a.name.localeCompare(b.name)
                                    : b.name.localeCompare(a.name)
                                )
                                .map((college) => (
                                    <div
                                        key={college.id}
                                        onClick={() => handleSelectCollege(college)}
                                        className={`p-3 rounded-lg cursor-pointer border transition-all ${selectedCollege?.id === college.id
                                            ? 'bg-emerald-900/20 border-emerald-500/50 shadow-md'
                                            : 'bg-slate-800/50 border-slate-700 hover:border-slate-500'
                                            }`}
                                    >
                                        <div className="font-bold text-white">{college.name}</div>
                                        <div className="flex justify-between items-center mt-2 text-xs text-slate-400">
                                            <span className="flex items-center gap-1"><MapPin className="w-3 h-3" /> {college.location || 'USA'}</span>
                                            <div className="flex items-center gap-2">
                                                {(gender === 'M' ? college.mensPowerRating : college.womensPowerRating) && (
                                                    <span className="text-emerald-500 font-bold">{gender === 'M' ? college.mensPowerRating : college.womensPowerRating}</span>
                                                )}
                                                <span className="bg-slate-700 px-1.5 py-0.5 rounded text-slate-300">{college.division || 'NCAA'}</span>
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            {results.length === 0 && !searching && (
                                <div className="text-center text-slate-500 py-10">No colleges found.</div>
                            )}
                        </div>
                    </div>
                )}

                {/* Roster View */}
                <div className="lg:col-span-2">
                    {selectedCollege ? (
                        <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden min-h-[600px] flex flex-col shadow-xl">
                            {/* College Header */}
                            <div className="bg-slate-950 p-6 border-b border-slate-800 flex justify-between items-start">
                                <div>
                                    <h2 className="text-2xl font-bold text-white mb-2">{selectedCollege.name}</h2>
                                    <div className="flex gap-3 text-sm text-slate-400">
                                        <span className="flex items-center gap-1"><MapPin className="w-4 h-4" /> {selectedCollege.location || 'Unknown Location'}</span>
                                        <span>•</span>
                                        <span className="text-emerald-400 font-medium">
                                            Power Rating: {gender === 'M' ? (selectedCollege.mensPowerRating || '-') : (selectedCollege.womensPowerRating || '-')}
                                        </span>
                                    </div>
                                </div>
                                {selectedCollege.url && (
                                    <a href={`https://${selectedCollege.url}`} target="_blank" rel="noopener noreferrer" className="text-slate-500 hover:text-white transition-colors">
                                        <ExternalLink className="w-5 h-5" />
                                    </a>
                                )}
                            </div>

                            {/* Roster Table */}
                            <div className="flex-1 overflow-x-auto">
                                {loading ? (
                                    <div className="flex flex-col items-center justify-center h-64 text-slate-500">
                                        <Loader2 className="w-8 h-8 animate-spin text-emerald-500 mb-2" />
                                        Loading Roster...
                                    </div>
                                ) : roster.length > 0 ? (
                                    <table className="w-full text-left text-sm">
                                        <thead className="bg-slate-950/50 text-slate-400 uppercase text-xs font-semibold">
                                            <tr>
                                                <th className="px-6 py-3">Player</th>
                                                <th className="px-6 py-3 text-center">UTR</th>
                                                <th className="px-6 py-3 text-center">Year</th>
                                                <th className="px-6 py-3 text-right">Nationality</th>
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y divide-slate-800">
                                            {roster.map((player) => (
                                                <tr key={player.id} className="hover:bg-slate-800/30 transition-colors group">
                                                    <td className="px-6 py-4 font-medium text-white group-hover:text-emerald-400 transition-colors">
                                                        <span
                                                            className="cursor-pointer hover:underline decoration-emerald-500/50 underline-offset-4"
                                                            onClick={(e) => {
                                                                e.stopPropagation();
                                                                onPlayerClick && onPlayerClick({
                                                                    player_id: player.id,
                                                                    name: player.name,
                                                                    utr_singles: player.utr,
                                                                    utr_doubles: player.doublesUtr,
                                                                    college: selectedCollege.name
                                                                });
                                                            }}
                                                        >
                                                            {player.name}
                                                        </span>
                                                    </td>
                                                    <td className="px-6 py-4 text-center">
                                                        <span className="bg-slate-800 px-2 py-1 rounded text-emerald-400 font-mono font-bold">
                                                            {player.utr ? Number(player.utr).toFixed(2) : '-'}
                                                        </span>
                                                    </td>
                                                    <td className="px-6 py-4 text-center text-slate-400">
                                                        {player.gradYear || player.year || '-'}
                                                    </td>
                                                    <td className="px-6 py-4 text-right text-slate-400">
                                                        {player.nationality || 'USA'}
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                ) : (
                                    <div className="flex flex-col items-center justify-center h-64 text-slate-500">
                                        <Users className="w-12 h-12 mb-4 opacity-20" />
                                        No roster data available.
                                    </div>
                                )}
                            </div>
                        </div>
                    ) : (
                        <div className="bg-slate-900/50 border-2 border-dashed border-slate-800 rounded-xl h-[600px] flex flex-col items-center justify-center text-slate-500">
                            <GraduationCap className="w-16 h-16 mb-4 opacity-20" />
                            <p className="text-lg">Select a college to view roster</p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default CollegeScout;
