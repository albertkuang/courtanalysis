import React, { useMemo } from 'react';
import { Search, TrendingUp, TrendingDown, Eye, Star } from 'lucide-react';
import { SelectFilter, SortableHeader, StatBadge } from '../components/shared';

const ScoutView = ({
    players,
    loading,
    search,
    setSearch,
    country,
    setCountry,
    gender,
    setGender,
    category,
    setCategory,
    sortConfig,
    handleSort,
    handlePlayerClick,
    selectedPlayerId,
    addToCompare,
    toggleFavorite,
    user
}) => {

    const sortedPlayers = useMemo(() => {
        if (!players) return [];
        const sorted = [...players];
        sorted.sort((a, b) => {
            let aVal = a[sortConfig.key];
            let bVal = b[sortConfig.key];

            if (aVal === null || aVal === undefined) aVal = '';
            if (bVal === null || bVal === undefined) bVal = '';

            if (typeof aVal === 'string') {
                aVal = aVal.toLowerCase();
                bVal = bVal.toLowerCase();
            }

            if (aVal < bVal) return sortConfig.direction === 'asc' ? -1 : 1;
            if (aVal > bVal) return sortConfig.direction === 'asc' ? 1 : -1;
            return 0;
        });
        return sorted;
    }, [players, sortConfig]);

    return (
        <div className="flex flex-col h-full overflow-hidden">
            {/* FILTERS BAR */}
            <div className="p-4 border-b border-slate-800 bg-slate-900/50 backdrop-blur flex flex-col md:flex-row gap-3 md:items-center justify-between overflow-x-auto shrink-0">
                <div className="flex flex-col md:flex-row gap-2 w-full md:w-auto">
                    <div className="relative w-full md:w-64">
                        <Search className="absolute left-3 top-2.5 text-slate-500 w-4 h-4" />
                        <input
                            type="text"
                            placeholder="Search..."
                            className="w-full bg-slate-800 border border-slate-700 rounded-lg pl-10 pr-4 py-2 text-sm focus:outline-none focus:border-tennis-blue placeholder-slate-500 text-white"
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                        />
                    </div>

                    <div className="flex gap-2 overflow-x-auto pb-1 md:pb-0">
                        <SelectFilter value={country} onChange={setCountry} options={[
                            { val: 'ALL', txt: 'All Countries' }, { val: 'USA', txt: 'USA' }, { val: 'CAN', txt: 'Canada' },
                            { val: 'GBR', txt: 'UK' }, { val: 'ESP', txt: 'Spain' }, { val: 'FRA', txt: 'France' }
                        ]} />
                        <SelectFilter value={gender} onChange={setGender} options={[
                            { val: 'M', txt: 'Men' }, { val: 'F', txt: 'Women' }
                        ]} width="w-24" />
                    </div>
                </div>
                <div className="hidden md:flex">
                    <StatBadge label="Players" value={players?.length || 0} />
                </div>
            </div>

            {/* TABLE CONTENT */}
            <div className="flex-1 overflow-auto p-2 md:p-6 pb-24 md:pb-6">
                <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-2xl">
                    {/* MOBILE CARD VIEW */}
                    <div className="md:hidden divide-y divide-slate-800">
                        {loading ? (
                            <div className="p-8 text-center text-slate-500">Loading data...</div>
                        ) : (
                            sortedPlayers.map((p) => (
                                <div
                                    key={p.player_id}
                                    onClick={() => handlePlayerClick(p)}
                                    className={`p-4 active:bg-slate-800 transition-colors ${selectedPlayerId === p.player_id ? 'bg-slate-800/80 border-l-2 border-tennis-green' : ''}`}
                                >
                                    <div className="flex justify-between items-start mb-2">
                                        <div className="flex items-center gap-2">
                                            <span className={`w-2 h-2 rounded-full ${p.gender === 'F' ? 'bg-pink-500' : 'bg-blue-500'}`}></span>
                                            <div>
                                                <div className="font-bold text-white text-base">{p.name}</div>
                                                <div className="text-xs text-slate-500">{p.country || 'Unknown'} • {p.age || '?'} yo</div>
                                            </div>
                                        </div>
                                        <div className="text-right">
                                            <div className="font-mono font-bold text-tennis-green text-lg">{p.utr_singles?.toFixed(2)}</div>
                                            {p.year_delta !== undefined && (
                                                <div className={`text-xs font-bold flex items-center justify-end gap-1 ${p.year_delta > 0 ? 'text-emerald-400' : p.year_delta < 0 ? 'text-rose-400' : 'text-slate-400'}`}>
                                                    {p.year_delta > 0 ? '+' : ''}{p.year_delta?.toFixed(2)}
                                                </div>
                                            )}
                                        </div>
                                    </div>

                                    <div className="flex justify-between items-center mt-3">
                                        <div className="text-xs text-slate-500 truncate max-w-[150px]">
                                            {p.college && <span className="bg-slate-800 px-2 py-1 rounded text-slate-400">{p.college}</span>}
                                        </div>
                                        <div className="flex gap-2">
                                            <button
                                                onClick={(e) => { e.stopPropagation(); toggleFavorite && toggleFavorite(p.player_id); }}
                                                className="p-2 bg-slate-800 rounded-lg text-slate-400 active:text-amber-400 active:bg-slate-700"
                                            >
                                                <Star className="w-4 h-4" />
                                            </button>
                                            <button
                                                onClick={(e) => { e.stopPropagation(); handlePlayerClick(p); }}
                                                className="px-3 py-2 bg-tennis-blue text-white rounded-lg text-xs font-bold"
                                            >
                                                View Profile
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            ))
                        )}
                    </div>

                    {/* DESKTOP TABLE VIEW */}
                    <table className="hidden md:table w-full text-left text-sm border-collapse">
                        <thead className="bg-slate-950 text-slate-400 uppercase text-xs font-semibold tracking-wider sticky top-0 z-10">
                            <tr>
                                <SortableHeader label="Name" sortKey="name" currentSort={sortConfig} onSort={handleSort} />
                                <SortableHeader label="UTR" sortKey="utr_singles" currentSort={sortConfig} onSort={handleSort} align="center" />
                                <SortableHeader label="Trend" sortKey="year_delta" currentSort={sortConfig} onSort={handleSort} align="center" />
                                <th className="px-6 py-4">Country</th>
                                <SortableHeader label="Age" sortKey="age" currentSort={sortConfig} onSort={handleSort} />
                                <th className="px-6 py-4 hidden lg:table-cell">College</th>
                                <th className="px-6 py-4">Action</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800">
                            {loading ? (
                                <tr><td colSpan="7" className="p-8 text-center text-slate-500">Loading data...</td></tr>
                            ) : (
                                sortedPlayers.map((p) => (
                                    <tr
                                        key={p.player_id}
                                        onClick={() => handlePlayerClick(p)}
                                        className={`hover:bg-slate-800/50 cursor-pointer transition-colors ${selectedPlayerId === p.player_id ? 'bg-slate-800/80 border-l-2 border-tennis-green' : ''}`}
                                    >
                                        <td className="px-6 py-3 font-medium text-white max-w-[200px] truncate">
                                            {p.name}
                                        </td>
                                        <td className="px-6 py-3 text-center">
                                            <span className="font-mono font-bold text-tennis-green">{p.utr_singles?.toFixed(2)}</span>
                                        </td>
                                        <td className="px-6 py-3 text-center">
                                            {p.year_delta !== undefined ? (
                                                <div className={`inline-flex items-center px-2 py-0.5 rounded text-xs gap-1 font-bold ${p.year_delta > 0 ? 'text-emerald-400 bg-emerald-400/10' : p.year_delta < 0 ? 'text-rose-400 bg-rose-400/10' : 'text-slate-400 bg-slate-400/10'}`}>
                                                    {p.year_delta > 0 ? <TrendingUp className="w-3 h-3" /> : p.year_delta < 0 ? <TrendingDown className="w-3 h-3" /> : null}
                                                    {p.year_delta > 0 ? '+' : ''}{p.year_delta?.toFixed(2)}
                                                </div>
                                            ) : (
                                                <span className="text-slate-600">-</span>
                                            )}
                                        </td>
                                        <td className="px-6 py-3 text-slate-400">{p.country || '-'}</td>
                                        <td className="px-6 py-3 text-slate-400">{p.age || '-'}</td>
                                        <td className="px-6 py-3 text-slate-500 hidden lg:table-cell truncate max-w-[200px]">{p.college || '-'}</td>
                                        <td className="px-6 py-3">
                                            <div className="flex items-center gap-2">
                                                <button
                                                    onClick={(e) => { e.stopPropagation(); handlePlayerClick(p); }}
                                                    className="text-xs bg-slate-800 hover:bg-tennis-green hover:text-white px-3 py-1.5 rounded border border-slate-700 transition-colors text-white flex items-center gap-1"
                                                >
                                                    <Eye className="w-3 h-3" /> View
                                                </button>
                                                <button
                                                    onClick={(e) => { e.stopPropagation(); toggleFavorite && toggleFavorite(p.player_id); }}
                                                    className="text-xs bg-slate-800 hover:bg-amber-500/20 hover:text-amber-400 px-2 py-1.5 rounded border border-slate-700 transition-colors text-slate-400"
                                                >
                                                    <Star className="w-3 h-3" />
                                                </button>
                                                <button
                                                    onClick={(e) => { e.stopPropagation(); addToCompare(p); }}
                                                    className="text-xs bg-slate-800 hover:bg-tennis-blue hover:text-white px-2 py-1.5 rounded border border-slate-700 transition-colors text-white"
                                                >
                                                    + Cp
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                    {!loading && sortedPlayers.length === 0 && (
                        <div className="md:p-12 p-8 text-center text-slate-500">
                            No players found matching your filters.
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default ScoutView;
