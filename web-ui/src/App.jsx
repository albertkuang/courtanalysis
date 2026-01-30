import React, { useState, useEffect, useMemo } from 'react';
import axios from 'axios';
import {
  Trophy, Search, Users, Activity, TrendingUp, ChevronRight,
  MapPin, Calendar, ExternalLink, X, ArrowUpDown, Menu, Lightbulb, TrendingDown,
  FileText, Download, Loader2
} from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';

function App() {
  // Data States
  const [players, setPlayers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [matchHistory, setMatchHistory] = useState([]);
  const [ratingHistory, setRatingHistory] = useState([]);

  // Filters
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('junior');
  const [country, setCountry] = useState('ALL');
  const [gender, setGender] = useState('M');

  // UI States
  const [view, setView] = useState('scout'); // scout, compare, tournaments
  const [selectedPlayer, setSelectedPlayer] = useState(null);
  const [compareList, setCompareList] = useState([]);
  const [tournaments, setTournaments] = useState([]);
  const [minUtr, setMinUtr] = useState(0);

  // Sorting State
  const [sortConfig, setSortConfig] = useState({ key: 'utr_singles', direction: 'desc' });

  useEffect(() => {
    if (view === 'tournaments') {
      fetchTournaments();
    } else {
      fetchPlayers();
    }
  }, [search, category, country, gender, view]);

  // Fetch Logic
  const fetchTournaments = async () => {
    try {
      const res = await axios.get('/api/tournaments');
      setTournaments(res.data.data);
    } catch (err) { console.error(err); }
  };

  const fetchPlayers = async () => {
    setLoading(true);
    try {
      const res = await axios.get('/api/players', {
        params: { search, category, country, gender, limit: 1000 }
      });
      setPlayers(res.data.data);
    } catch (err) { console.error(err); }
    setLoading(false);
  };

  const fetchPlayerDetails = async (id) => {
    try {
      const [matchesRes, historyRes] = await Promise.all([
        axios.get(`/api/players/${id}/matches`),
        axios.get(`/api/players/${id}/history`)
      ]);
      setMatchHistory(matchesRes.data.data);
      setRatingHistory(historyRes.data.data);
    } catch (err) { console.error(err); }
  };

  // Handlers
  const handlePlayerClick = (player) => {
    setSelectedPlayer(player);
    fetchPlayerDetails(player.player_id);
  };

  const addToCompare = (player) => {
    if (compareList.find(p => p.player_id === player.player_id)) return;
    const newList = compareList.length >= 2 ? [compareList[0], player] : [...compareList, player];
    setCompareList(newList);
    setView('compare');
  };

  const handleSort = (key) => {
    let direction = 'desc';
    if (sortConfig.key === key && sortConfig.direction === 'desc') {
      direction = 'asc';
    }
    setSortConfig({ key, direction });
  };

  // Derived State (Sorting)
  const sortedPlayers = useMemo(() => {
    if (!players) return [];
    const sorted = [...players];
    sorted.sort((a, b) => {
      let aVal = a[sortConfig.key];
      let bVal = b[sortConfig.key];

      // Handle nulls
      if (aVal === null) aVal = '';
      if (bVal === null) bVal = '';

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
    <div className="flex flex-col md:flex-row h-screen bg-tennis-dark text-slate-200 overflow-hidden font-sans">

      {/* DESKTOP SIDEBAR (Hidden on Mobile) */}
      <div className="hidden md:flex w-64 bg-slate-900 border-r border-slate-800 p-4 flex-col">
        <BrandHeader />
        <NavMenu view={view} setView={setView} />
        <div className="text-xs text-slate-600 mt-auto">v2.0 Mobile Ready</div>
      </div>

      {/* MOBILE HEADER (Visible only on Mobile) */}
      <div className="md:hidden h-14 bg-slate-900 border-b border-slate-800 flex items-center px-4 justify-between shrink-0">
        <BrandHeader small />
        <div className="flex gap-2">
          <StatBadge label="Total" value={players.length} small />
        </div>
      </div>

      {/* MAIN CONTENT AREA */}
      <div className="flex-1 flex flex-col min-w-0 bg-tennis-dark relative">

        {/* FILTERS BAR (Scout View) */}
        {view === 'scout' && (
          <div className="p-4 border-b border-slate-800 bg-slate-900/50 backdrop-blur flex flex-col md:flex-row gap-3 md:items-center justify-between overflow-x-auto">
            <div className="flex flex-col md:flex-row gap-2 w-full md:w-auto">
              <div className="relative w-full md:w-64">
                <Search className="absolute left-3 top-2.5 text-slate-500 w-4 h-4" />
                <input
                  type="text"
                  placeholder="Search..."
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg pl-10 pr-4 py-2 text-sm focus:outline-none focus:border-tennis-blue placeholder-slate-500"
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
                <SelectFilter value={category} onChange={setCategory} options={[
                  { val: 'junior', txt: 'Juniors' }, { val: 'college', txt: 'College' }, { val: 'adult', txt: 'Pro' }
                ]} width="w-28" />
              </div>
            </div>
            <div className="hidden md:flex">
              <StatBadge label="Players" value={players.length} />
            </div>
          </div>
        )}

        {/* FILTERS BAR (Insights View) */}
        {view === 'insights' && (
          <div className="p-4 border-b border-slate-800 bg-slate-900/50 backdrop-blur flex flex-col md:flex-row gap-3 md:items-center justify-between overflow-x-auto">
            <div className="flex flex-col md:flex-row gap-2 w-full md:w-auto">
              <div className="flex gap-2 overflow-x-auto pb-1 md:pb-0 items-center">
                <SelectFilter value={country} onChange={setCountry} options={[
                  { val: 'ALL', txt: 'All Countries' }, { val: 'USA', txt: 'USA' }, { val: 'CAN', txt: 'Canada' },
                  { val: 'GBR', txt: 'UK' }, { val: 'ESP', txt: 'Spain' }, { val: 'FRA', txt: 'France' }
                ]} />
                <SelectFilter value={gender} onChange={setGender} options={[
                  { val: 'M', txt: 'Men' }, { val: 'F', txt: 'Women' }
                ]} width="w-24" />
                <SelectFilter value={category} onChange={setCategory} options={[
                  { val: 'junior', txt: 'Juniors' }, { val: 'college', txt: 'College' }, { val: 'adult', txt: 'Pro' }
                ]} width="w-28" />
                <div className="flex items-center gap-2 bg-slate-800 border border-slate-700 rounded-lg px-3 py-2">
                  <span className="text-xs text-slate-400 whitespace-nowrap">Min UTR: {minUtr}</span>
                  <input
                    type="range" min="0" max="16" step="0.5"
                    value={minUtr} onChange={(e) => setMinUtr(parseFloat(e.target.value))}
                    className="w-24 accent-tennis-blue cursor-pointer"
                  />
                </div>
              </div>
            </div>
            <StatBadge label="Analyzed" value={players.length} />
          </div>
        )}

        {/* VIEW CONTENT */}
        <div className="flex-1 overflow-auto p-2 md:p-6 pb-24 md:pb-6"> {/* pb-24 for mobile nav space */}

          {view === 'scout' && (
            <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-2xl">
              <table className="w-full text-left text-sm">
                <thead className="bg-slate-950 text-slate-400 uppercase text-xs font-semibold tracking-wider sticky top-0 z-10">
                  <tr>
                    <SortableHeader label="Name" sortKey="name" currentSort={sortConfig} onSort={handleSort} />
                    <SortableHeader label="UTR" sortKey="utr_singles" currentSort={sortConfig} onSort={handleSort} align="center" />
                    <th className="px-3 md:px-6 py-4 text-center hidden md:table-cell">Trend</th>
                    <th className="px-3 md:px-6 py-4 hidden sm:table-cell">Country</th>
                    <SortableHeader label="Age" sortKey="age" currentSort={sortConfig} onSort={handleSort} className="hidden sm:table-cell" />
                    <th className="px-3 md:px-6 py-4 hidden lg:table-cell">College</th>
                    <th className="px-3 md:px-6 py-4">Action</th>
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
                        className={`hover:bg-slate-800/50 cursor-pointer transition-colors ${selectedPlayer?.player_id === p.player_id ? 'bg-slate-800/80 border-l-2 border-tennis-green' : ''}`}
                      >
                        <td className="px-3 md:px-6 py-3 font-medium text-white max-w-[150px] truncate">
                          <div className="flex items-center gap-2">
                            <span className={`w-1.5 h-1.5 rounded-full ${p.gender === 'F' ? 'bg-pink-500' : 'bg-blue-500'} md:hidden`}></span>
                            {p.name}
                          </div>
                        </td>
                        <td className="px-3 md:px-6 py-3 text-center">
                          <span className="font-mono font-bold text-tennis-green">{p.utr_singles?.toFixed(2)}</span>
                        </td>
                        <td className="px-3 md:px-6 py-3 text-center hidden md:table-cell">
                          <div className="inline-flex items-center text-emerald-400 bg-emerald-400/10 px-2 py-0.5 rounded text-xs gap-1">
                            <TrendingUp className="w-3 h-3" /> Good
                          </div>
                        </td>
                        <td className="px-3 md:px-6 py-3 text-slate-400 hidden sm:table-cell">{p.country || '-'}</td>
                        <td className="px-3 md:px-6 py-3 text-slate-400 hidden sm:table-cell">{p.age || '-'}</td>
                        <td className="px-3 md:px-6 py-3 text-slate-500 hidden lg:table-cell truncate max-w-[120px]">{p.college || '-'}</td>
                        <td className="px-3 md:px-6 py-3">
                          <button
                            onClick={(e) => { e.stopPropagation(); addToCompare(p); }}
                            className="text-xs bg-slate-800 hover:bg-tennis-blue hover:text-white px-2 py-1 rounded border border-slate-700 transition-colors"
                          >
                            + Cp
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          )}

          {view === 'tournaments' && (
            <TournamentList tournaments={tournaments} />
          )}

          {view === 'report' && (
            <ReportView />
          )}

          {view === 'insights' && (
            <InsightsView players={players} minUtr={minUtr} onPlayerClick={handlePlayerClick} />
          )}

          {view === 'compare' && (
            <ComparisonView list={compareList} onRemove={(id) => setCompareList(compareList.filter(c => c.player_id !== id))} />
          )}

        </div>
      </div>

      {/* MOBILE BOTTOM NAV */}
      <div className="md:hidden fixed bottom-0 left-0 w-full bg-slate-900 border-t border-slate-800 flex justify-around p-2 z-40 pb-safe">
        <MobileNavItem icon={<Users />} label="Scout" active={view === 'scout'} onClick={() => setView('scout')} />
        <MobileNavItem icon={<Lightbulb />} label="Insights" active={view === 'insights'} onClick={() => setView('insights')} />
        <MobileNavItem icon={<FileText />} label="Report" active={view === 'report'} onClick={() => setView('report')} />
        <MobileNavItem icon={<Activity />} label="Compare" active={view === 'compare'} onClick={() => setView('compare')} />
        <MobileNavItem icon={<MapPin />} label="Events" active={view === 'tournaments'} onClick={() => setView('tournaments')} />
      </div>

      {/* PLAYER DETAIL SLIDE-OVER (Responsive) */}
      {
        selectedPlayer && (
          <div className="fixed inset-0 z-50 flex justify-end bg-black/50 backdrop-blur-sm animate-in fade-in duration-200">
            {/* Click backdrop to close */}
            <div className="absolute inset-0" onClick={() => setSelectedPlayer(null)}></div>

            <div className="relative w-full md:w-96 h-full bg-slate-900 border-l border-slate-800 shadow-2xl overflow-y-auto animate-in slide-in-from-right duration-300">
              <button
                onClick={() => setSelectedPlayer(null)}
                className="absolute top-4 right-4 p-2 bg-black/20 hover:bg-rose-500/20 text-white hover:text-rose-500 rounded-full transition-colors z-10"
              >
                <X className="w-5 h-5" />
              </button>

              <PlayerHeader player={selectedPlayer} />

              <div className="p-4 md:p-6 space-y-6">
                <RatingChart history={ratingHistory} />
                <HeadToHeadSection matches={matchHistory} playerId={selectedPlayer.player_id} />
                <MatchLog matches={matchHistory} playerId={selectedPlayer.player_id} />
              </div>
            </div>
          </div>
        )
      }

    </div >
  );
}

// --- Sub Components ---

const HeadToHeadSection = ({ matches, playerId }) => {
  const [opponentId, setOpponentId] = useState('');

  // derived unique opponents
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
                <div key={m.match_id} className="text-xs flex justify-between p-2 bg-slate-900/50 rounded border border-slate-800/50">
                  <span className={isWin ? 'text-tennis-green' : 'text-rose-400'}>{isWin ? 'W' : 'L'}</span>
                  <span className="text-slate-400">{m.date.split('T')[0]}</span>
                  <span className="text-slate-300 font-mono">{m.score}</span>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  );
};

const BrandHeader = ({ small }) => (
  <div className={`flex items-center gap-3 ${small ? '' : 'mb-8 px-2'}`}>
    <div className="bg-tennis-green p-1.5 md:p-2 rounded-lg">
      <Trophy className="text-slate-900 w-5 h-5 md:w-6 md:h-6" />
    </div>
    <h1 className="text-lg md:text-xl font-bold text-white tracking-tight">
      CourtSide <span className={`text-tennis-blue ${small ? 'inline font-normal ml-1' : 'block text-xs font-medium'}`}>ANALYTICS</span>
    </h1>
  </div>
);

const NavMenu = ({ view, setView }) => (
  <nav className="space-y-2 flex-1">
    <NavItem icon={<Users />} label="Scout" active={view === 'scout'} onClick={() => setView('scout')} />
    <NavItem icon={<Lightbulb />} label="Insights" active={view === 'insights'} onClick={() => setView('insights')} />
    <NavItem icon={<FileText />} label="Report" active={view === 'report'} onClick={() => setView('report')} />
    <NavItem icon={<Activity />} label="Compare" active={view === 'compare'} onClick={() => setView('compare')} />
    <NavItem icon={<MapPin />} label="Tournaments" active={view === 'tournaments'} onClick={() => setView('tournaments')} />
  </nav>
);

const NavItem = ({ icon, label, active, onClick }) => (
  <div onClick={onClick} className={`flex items-center gap-3 px-3 py-2 rounded-lg cursor-pointer transition-colors ${active ? 'bg-tennis-blue/10 text-tennis-blue' : 'text-slate-400 hover:text-white hover:bg-slate-800'}`}>
    {React.cloneElement(icon, { size: 18 })}
    <span className="text-sm font-medium">{label}</span>
    {active && <ChevronRight className="ml-auto w-4 h-4 opacity-50" />}
  </div>
);

const MobileNavItem = ({ icon, label, active, onClick }) => (
  <div onClick={onClick} className={`flex flex-col items-center gap-1 p-2 rounded-lg ${active ? 'text-tennis-blue' : 'text-slate-500'}`}>
    {React.cloneElement(icon, { size: 20 })}
    <span className="text-[10px] font-medium">{label}</span>
  </div>
);

const SortableHeader = ({ label, sortKey, currentSort, onSort, align = 'left', className = '' }) => (
  <th
    className={`px-3 md:px-6 py-4 cursor-pointer hover:text-white transition-colors text-${align} ${className}`}
    onClick={() => onSort(sortKey)}
  >
    <div className={`flex items-center gap-1 ${align === 'center' ? 'justify-center' : ''}`}>
      {label}
      <ArrowUpDown className={`w-3 h-3 ${currentSort.key === sortKey ? 'text-tennis-blue' : 'opacity-30'}`} />
    </div>
  </th>
);

const SelectFilter = ({ value, onChange, options, width = 'w-auto' }) => (
  <select
    value={value}
    onChange={(e) => onChange(e.target.value)}
    className={`bg-slate-800 border border-slate-700 rounded-lg px-2 py-2 text-xs md:text-sm focus:outline-none text-white ${width}`}
  >
    {options.map(o => <option key={o.val} value={o.val}>{o.txt}</option>)}
  </select>
);

const StatBadge = ({ label, value, small }) => (
  <div className={`flex items-center gap-2 px-3 py-1.5 bg-slate-800 rounded-full border border-slate-700 ${small ? 'scale-90 origin-right' : ''}`}>
    <span className="text-xs text-slate-400">{label}</span>
    <span className="text-sm font-bold text-white">{value}</span>
  </div>
);

// --- Content Components ---

const PlayerHeader = ({ player }) => (
  <div className="p-6 border-b border-slate-800 bg-gradient-to-b from-slate-800 to-slate-900 pt-12 md:pt-6">
    <div className="flex justify-between items-start mb-4">
      <div className="bg-slate-800 p-2 rounded text-xs font-mono text-slate-400 border border-slate-700">ID: {player.player_id}</div>
      <a href={`https://app.utrsports.net/profiles/${player.player_id}`} target="_blank" rel="noreferrer" className="text-tennis-blue hover:text-white mr-8 md:mr-0">
        <ExternalLink className="w-4 h-4" />
      </a>
    </div>
    <h2 className="text-2xl font-bold text-white mb-1">{player.name}</h2>
    <div className="flex items-center gap-2 text-sm text-slate-400 mb-6">
      <MapPin className="w-3 h-3" /> {player.location || player.country || 'Unknown'}
    </div>

    <div className="grid grid-cols-2 gap-3">
      <div className="bg-slate-950 p-4 rounded-xl border border-slate-800">
        <div className="text-slate-500 text-xs uppercase font-semibold mb-1">Singles UTR</div>
        <div className="text-3xl font-bold text-tennis-green">{player.utr_singles?.toFixed(2)}</div>
      </div>
      <div className="bg-slate-950 p-4 rounded-xl border border-slate-800">
        <div className="text-slate-500 text-xs uppercase font-semibold mb-1">Doubles UTR</div>
        <div className="text-xl font-bold text-slate-300">{player.utr_doubles?.toFixed(2) || '-'}</div>
      </div>
    </div>
  </div>
);

const RatingChart = ({ history }) => (
  <div>
    <h3 className="text-sm font-semibold text-white uppercase tracking-wider mb-4 flex items-center gap-2">
      <Activity className="w-4 h-4 text-tennis-blue" /> 1Y Trend
    </h3>
    <div className="h-40 bg-slate-950 rounded-lg border border-slate-800 p-2">
      {history && history.length > 0 ? (
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={history}>
            <Line type="monotone" dataKey="rating" stroke="#0ea5e9" strokeWidth={2} dot={false} />
            <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155' }} itemStyle={{ color: '#e2e8f0' }} />
          </LineChart>
        </ResponsiveContainer>
      ) : (
        <div className="flex items-center justify-center h-full text-slate-600 text-sm">No History</div>
      )}
    </div>
  </div>
);

const MatchLog = ({ matches, playerId }) => (
  <div>
    <h3 className="text-sm font-semibold text-white uppercase tracking-wider mb-4 flex items-center gap-2">
      <Calendar className="w-4 h-4 text-tennis-green" /> Recent Matches ({matches?.length || 0})
    </h3>
    <div className="space-y-3">
      {matches && matches.slice(0, 20).map((m) => {
        const isWinner = String(m.winner_id) === String(playerId);
        return (
          <div key={m.match_id} className="bg-slate-800/50 p-3 rounded-lg border border-slate-800 hover:border-slate-600 transition-colors">
            <div className="flex justify-between items-center mb-1">
              <span className={`text-xs font-bold px-1.5 py-0.5 rounded ${isWinner ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'}`}>
                {isWinner ? 'W' : 'L'}
              </span>
              <span className="text-xs text-slate-500">{m.date?.split('T')[0]}</span>
            </div>
            <div className="text-sm font-medium text-slate-200 truncate">
              vs {isWinner ? m.loser_name : m.winner_name}
            </div>
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

const TournamentList = ({ tournaments }) => (
  <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-2xl">
    <table className="w-full text-left text-sm">
      <thead className="bg-slate-950 text-slate-400 uppercase text-xs font-semibold tracking-wider">
        <tr>
          <th className="px-6 py-4">Tournament</th>
          <th className="px-6 py-4 text-center">Matches</th>
          <th className="px-6 py-4 text-right hidden sm:table-cell">Date</th>
        </tr>
      </thead>
      <tbody className="divide-y divide-slate-800">
        {tournaments.map((t, i) => (
          <tr key={i} className="hover:bg-slate-800/50 transition-colors">
            <td className="px-6 py-4 font-medium text-white">{t.tournament}</td>
            <td className="px-6 py-4 text-center font-mono text-tennis-blue">{t.match_count}</td>
            <td className="px-6 py-4 text-right text-slate-400 hidden sm:table-cell">{t.last_date?.split('T')[0]}</td>
          </tr>
        ))}
      </tbody>
    </table>
  </div>
);


const InsightsView = ({ players, minUtr, onPlayerClick }) => {
  // Filter by Min UTR
  const filtered = useMemo(() => {
    return players.filter(p => (p.utr_singles || 0) >= minUtr);
  }, [players, minUtr]);

  // 1. Comeback Wins (Highest Count)
  const comebackKings = useMemo(() => {
    return [...filtered].sort((a, b) => (b.comeback_wins || 0) - (a.comeback_wins || 0)).slice(0, 10);
  }, [filtered]);

  // 2. Risers (Year Delta > 0)
  const risers = useMemo(() => {
    return filtered.filter(p => (p.year_delta || 0) > 0)
      .sort((a, b) => b.year_delta - a.year_delta).slice(0, 10);
  }, [filtered]);

  // 3. Fallers (Year Delta < 0)
  const fallers = useMemo(() => {
    return filtered.filter(p => (p.year_delta || 0) < 0)
      .sort((a, b) => a.year_delta - b.year_delta).slice(0, 10); // Most negative first
  }, [filtered]);

  // 4. Clutch Players (Tiebreak% > 60% AND 3-Set% > 60%)
  const clutchPlayers = useMemo(() => {
    return filtered.filter(p => {
      const tbTotal = (p.tiebreak_wins || 0) + (p.tiebreak_losses || 0);
      const tsTotal = (p.three_set_wins || 0) + (p.three_set_losses || 0);

      if (tbTotal < 2 || tsTotal < 2) return false; // Minimum sample size

      const tbPct = (p.tiebreak_wins / tbTotal) * 100;
      const tsPct = (p.three_set_wins / tsTotal) * 100;

      return tbPct >= 60 && tsPct >= 60;
    }).sort((a, b) => (b.three_set_wins || 0) - (a.three_set_wins || 0)).slice(0, 10);
  }, [filtered]);

  const CardRow = ({ title, icon, data, type }) => (
    <div className="mb-8">
      <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
        {icon} {title}
      </h3>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        {data.map((p, i) => (
          <div
            key={p.player_id}
            onClick={() => onPlayerClick(p)}
            className="bg-slate-900 border border-slate-800 p-4 rounded-xl hover:bg-slate-800 transition-colors cursor-pointer group"
          >
            <div className="flex justify-between items-start mb-2">
              <span className="text-2xl font-bold text-slate-500 opacity-20 group-hover:opacity-40">#{i + 1}</span>
              <span className="font-mono text-tennis-blue font-bold">{p.utr_singles?.toFixed(2)}</span>
            </div>
            <div className="font-semibold text-white truncate mb-1">{p.name}</div>
            <div className="text-xs text-slate-400 mb-2">{p.country}</div>

            <div className="bg-slate-950 rounded p-2 text-center">
              {type === 'comeback' && (
                <div>
                  <span className="block text-xl font-bold text-tennis-green">{p.comeback_wins}</span>
                  <span className="text-[10px] uppercase text-slate-500">Comeback Wins</span>
                </div>
              )}
              {type === 'delta' && (
                <div>
                  <span className={`block text-xl font-bold ${p.year_delta > 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                    {p.year_delta > 0 ? '+' : ''}{p.year_delta?.toFixed(2)}
                  </span>
                  <span className="text-[10px] uppercase text-slate-500">1YR Change</span>
                </div>
              )}
              {type === 'clutch' && (
                <div className="flex justify-around">
                  <div>
                    <div className="text-sm font-bold text-white">
                      {Math.round((p.tiebreak_wins / (p.tiebreak_wins + p.tiebreak_losses)) * 100)}%
                    </div>
                    <div className="text-[8px] text-slate-500">TB</div>
                  </div>
                  <div>
                    <div className="text-sm font-bold text-white">
                      {Math.round((p.three_set_wins / (p.three_set_wins + p.three_set_losses)) * 100)}%
                    </div>
                    <div className="text-[8px] text-slate-500">3-Set</div>
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <CardRow
        title="Comeback Kings (Most wins after losing 1st set)"
        icon={<TrendingUp className="text-emerald-400" />}
        data={comebackKings}
        type="comeback"
      />

      <CardRow
        title="Fastest Risers (Top 1Y Growth)"
        icon={<Activity className="text-tennis-blue" />}
        data={risers}
        type="delta"
      />

      <CardRow
        title="Biggest Fallers (Top 1Y Drop)"
        icon={<TrendingDown className="text-rose-400" />}
        data={fallers}
        type="delta"
      />

      <CardRow
        title="Clutch Performers (>60% TB & 3-Set Win Rate)"
        icon={<Lightbulb className="text-yellow-400" />}
        data={clutchPlayers}
        type="clutch"
      />
    </div>
  );
};

const ReportView = () => {
  const [loading, setLoading] = useState(false);
  const [params, setParams] = useState({
    country: 'ALL',
    gender: 'M',
    category: 'junior',
    minUtr: 0,
    count: 100,
    name: ''
  });

  const generateReport = async () => {
    setLoading(true);
    try {
      const response = await axios.get('/api/export', {
        params: {
          country: params.country,
          gender: params.gender,
          category: params.category,
          count: params.count,
          name: params.name,
          min_utr: params.minUtr
        },
        responseType: 'blob', // Important
      });

      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;

      // Try to get filename from header or generate one
      const contentDisposition = response.headers['content-disposition'];
      let filename = 'report.xlsx';
      if (contentDisposition) {
        const match = contentDisposition.match(/filename="?([^"]+)"?/);
        if (match) filename = match[1];
      }

      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);

    } catch (err) {
      console.error(err);
      alert('Failed to generate report. Checks logs or ensure data exists.');
    }
    setLoading(false);
  };

  const handleChange = (key, val) => setParams(prev => ({ ...prev, [key]: val }));

  return (
    <div className="max-w-xl mx-auto mt-10 p-8 bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl animate-in fade-in zoom-in-95 duration-300">
      <div className="flex items-center gap-3 mb-6">
        <div className="bg-tennis-blue/20 p-2 rounded-lg">
          <FileText className="w-8 h-8 text-tennis-blue" />
        </div>
        <div>
          <h2 className="text-2xl font-bold text-white">Export Report</h2>
          <p className="text-slate-400 text-sm">Generate detailed Excel analysis for offline viewing.</p>
        </div>
      </div>

      <div className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-semibold text-slate-500 uppercase mb-1">Country</label>
            <SelectFilter value={params.country} onChange={(v) => handleChange('country', v)} width="w-full" options={[
              { val: 'ALL', txt: 'All Countries' }, { val: 'USA', txt: 'USA' }, { val: 'CAN', txt: 'Canada' },
              { val: 'GBR', txt: 'UK' }, { val: 'ESP', txt: 'Spain' }, { val: 'FRA', txt: 'France' }
            ]} />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-500 uppercase mb-1">Gender</label>
            <SelectFilter value={params.gender} onChange={(v) => handleChange('gender', v)} width="w-full" options={[
              { val: 'M', txt: 'Men' }, { val: 'F', txt: 'Women' }
            ]} />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-semibold text-slate-500 uppercase mb-1">Category</label>
            <SelectFilter value={params.category} onChange={(v) => handleChange('category', v)} width="w-full" options={[
              { val: 'junior', txt: 'Juniors' }, { val: 'college', txt: 'College' }, { val: 'adult', txt: 'Pro' }
            ]} />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-500 uppercase mb-1">Max Results</label>
            <input type="number" value={params.count} onChange={(e) => handleChange('count', e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white focus:border-tennis-blue focus:outline-none"
            />
          </div>
        </div>

        <div>
          <label className="block text-xs font-semibold text-slate-500 uppercase mb-1">Minimum UTR ({params.minUtr})</label>
          <input type="range" min="0" max="16" step="0.5" value={params.minUtr} onChange={(e) => handleChange('minUtr', parseFloat(e.target.value))} className="w-full accent-tennis-blue" />
        </div>

        <div>
          <label className="block text-xs font-semibold text-slate-500 uppercase mb-1">Specific Player (Optional)</label>
          <input type="text" placeholder="Search by name..." value={params.name} onChange={(e) => handleChange('name', e.target.value)}
            className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white focus:border-tennis-blue focus:outline-none placeholder-slate-600"
          />
        </div>

        <button
          onClick={generateReport}
          disabled={loading}
          className="w-full mt-4 bg-gradient-to-r from-tennis-blue to-cyan-500 hover:from-cyan-500 hover:to-tennis-blue text-white font-bold py-3 rounded-xl transition-all shadow-lg shadow-tennis-blue/20 flex items-center justify-center gap-2"
        >
          {loading ? <Loader2 className="animate-spin" /> : <Download />}
          {loading ? 'Generating Report...' : 'Download Excel Report'}
        </button>
      </div>
    </div>
  );
};

const ComparisonView = ({ list, onRemove }) => (
  <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-4xl mx-auto">
    {list.length === 0 && (
      <div className="col-span-1 md:col-span-2 text-center text-slate-500 py-20 border-2 border-dashed border-slate-800 rounded-xl">
        Select players (+Cp) to compare
      </div>
    )}
    {list.map((p) => (
      <div key={p.player_id} className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-2xl relative overflow-hidden">
        <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-tennis-blue to-tennis-green"></div>
        <div className="flex justify-between items-start mb-6">
          <div>
            <div className="text-2xl md:text-3xl font-bold text-white mb-1">{p.name}</div>
            <div className="text-sm text-slate-400">{p.country} &bull; {p.age || '?'}</div>
          </div>
          <div className="text-3xl md:text-4xl font-mono font-bold text-tennis-green">{p.utr_singles?.toFixed(2)}</div>
        </div>

        <div className="space-y-4">
          <div className="flex justify-between py-2 border-b border-slate-800">
            <span className="text-slate-500 text-sm uppercase">Doubles</span>
            <span className="text-white font-mono">{p.utr_doubles?.toFixed(2) || '-'}</span>
          </div>
          <div className="flex justify-between py-2 border-b border-slate-800">
            <span className="text-slate-500 text-sm uppercase">College</span>
            <span className="text-white text-right max-w-[150px] truncate">{p.college || '-'}</span>
          </div>
        </div>

        <div className="mt-8">
          <button onClick={() => onRemove(p.player_id)} className="w-full py-2 bg-slate-800 text-rose-400 rounded-lg hover:bg-slate-700 text-sm font-medium">Remove</button>
        </div>
      </div>
    ))}
  </div>
);

export default App;
