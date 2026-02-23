import { useState, useEffect } from 'react';
import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8004';

export default function TennisAbstractElo({ onPlayerClick }) {
  const [tour, setTour] = useState('ATP');
  const [eloData, setEloData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchName, setSearchName] = useState('');
  const [searchResults, setSearchResults] = useState([]);

  // Use onPlayerClick from props or create internal handler
  const handlePlayerClick = async (player) => {
    console.log('[TennisAbstractElo] Player clicked:', player);
    console.log('[TennisAbstractElo] elo_id:', player.elo_id, 'player_name:', player.player_name);
    
    // Try to find the real player_id by looking up the player name in the main database
    let realPlayerId = null;
    let realPlayer = null;
    
    try {
      const response = await axios.get(`${API_BASE}/players`, {
        params: { 
          search: player.player_name,
          category: 'adult',
          limit: 5
        }
      });
      
      // Find best match by exact name match or first result
      const players = response.data?.data || [];
      if (players.length > 0) {
        // Try exact match first
        const exactMatch = players.find(p => 
          p.name?.toLowerCase() === player.player_name?.toLowerCase()
        );
        if (exactMatch) {
          realPlayerId = exactMatch.player_id;
          realPlayer = exactMatch;
        } else if (players.length > 0) {
          // Use first match as fallback
          realPlayerId = players[0].player_id;
          realPlayer = players[0];
        }
      }
    } catch (error) {
      console.error('[TennisAbstractElo] Error looking up player:', error);
    }
    
    if (onPlayerClick) {
      // Use the real player_id if found, otherwise pass elo info for reference
      onPlayerClick({ 
        player_id: realPlayerId || player.elo_id, 
        name: realPlayer?.name || player.player_name,
        // Include additional data
        elo_id: player.elo_id,
        elo_rating: player.elo_rating,
        elo_rank: player.elo_rank,
        official_rank: player.official_rank,
        age: player.age,
        tour: player.tour,
        // Include UTR if available from lookup
        utr_singles: realPlayer?.utr_singles,
        utr_doubles: realPlayer?.utr_doubles,
      });
    }
  };

  useEffect(() => {
    fetchEloData();
  }, [tour]);

  const fetchEloData = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API_BASE}/tennis-abstract/elo`, {
        params: { tour, limit: 50 }
      });
      setEloData(response.data.data || []);
    } catch (error) {
      console.error('Error fetching Elo data:', error);
    }
    setLoading(false);
  };

  const searchPlayer = async () => {
    if (!searchName.trim()) return;
    try {
      const response = await axios.get(`${API_BASE}/tennis-abstract/elo/${searchName}`);
      setSearchResults(response.data.data || []);
    } catch (error) {
      console.error('Error searching player:', error);
    }
  };

  return (
    <div className="p-4 md:p-6 bg-slate-950 min-h-screen">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white mb-2">Tennis Abstract Elo Rankings</h1>
        <p className="text-slate-400 text-sm">
          Elo ratings from tennisabstract.com - An alternative ranking based on match performance
        </p>
      </div>

      {/* Tour Selection */}
      <div className="flex gap-3 mb-6">
        <button
          onClick={() => setTour('ATP')}
          className={`px-4 py-2 rounded-lg font-medium transition-all ${
            tour === 'ATP' 
              ? 'bg-blue-600 text-white shadow-lg shadow-blue-900/50' 
              : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
          }`}
        >
          ATP
        </button>
        <button
          onClick={() => setTour('WTA')}
          className={`px-4 py-2 rounded-lg font-medium transition-all ${
            tour === 'WTA' 
              ? 'bg-pink-600 text-white shadow-lg shadow-pink-900/50' 
              : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
          }`}
        >
          WTA
        </button>
        <button
          onClick={fetchEloData}
          className="ml-auto px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-all"
        >
          Refresh Data
        </button>
      </div>

      {/* Search */}
      <div className="flex gap-2 mb-6">
        <input
          type="text"
          placeholder="Search player by name..."
          value={searchName}
          onChange={(e) => setSearchName(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && searchPlayer()}
          className="flex-1 px-4 py-2.5 bg-slate-900 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
        />
        <button
          onClick={searchPlayer}
          className="px-4 py-2.5 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-all"
        >
          Search
        </button>
      </div>

      {/* Search Results */}
      {searchResults.length > 0 && (
        <div className="mb-6 p-4 bg-slate-900/80 border border-slate-700 rounded-lg">
          <h3 className="font-semibold text-white mb-3">Search Results</h3>
          <div className="space-y-2">
            {searchResults.map((player) => (
              <div 
                key={player.elo_id} 
                onClick={() => handlePlayerClick(player)}
                className="flex items-center justify-between bg-slate-800 p-3 rounded-lg cursor-pointer hover:bg-slate-700 transition-all border border-slate-700 hover:border-indigo-500"
              >
                <div className="flex items-center gap-3">
                  <span className={`px-2 py-0.5 text-xs font-medium rounded ${
                    player.tour === 'ATP' ? 'bg-blue-900/50 text-blue-400' : 'bg-pink-900/50 text-pink-400'
                  }`}>
                    {player.tour}
                  </span>
                  <span className="font-medium text-white">{player.player_name}</span>
                </div>
                <div className="text-right">
                  <div className="font-bold text-white">Elo: {player.elo_rating}</div>
                  <div className="text-sm text-slate-400">
                    Rank #{player.elo_rank} (Official: #{player.official_rank})
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Main Rankings Table */}
      {loading ? (
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500"></div>
          <p className="mt-2 text-slate-400">Loading Elo rankings...</p>
        </div>
      ) : (
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-slate-800/80 border-b border-slate-700">
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">Rank</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">Player</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-slate-400 uppercase tracking-wider">Elo Rating</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-slate-400 uppercase tracking-wider">Official Rank</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-slate-400 uppercase tracking-wider">Age</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {eloData.map((player, index) => (
                  <tr 
                    key={player.elo_id} 
                    className={`hover:bg-slate-800/50 transition-all cursor-pointer ${
                      index < 10 ? 'bg-amber-900/10' : ''
                    }`}
                    onClick={() => handlePlayerClick(player)}
                  >
                    <td className="px-4 py-3">
                      <span className={`font-bold ${
                        player.elo_rank <= 3 ? 'text-yellow-400' : 
                        player.elo_rank <= 10 ? 'text-orange-400' : 'text-slate-300'
                      }`}>
                        #{player.elo_rank}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-white">
                          {player.player_name}
                        </span>
                        {index < 10 && (
                          <span className="text-amber-400">⭐</span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-white">
                      {player.elo_rating}
                    </td>
                    <td className="px-4 py-3 text-right text-slate-400">
                      #{player.official_rank || '-'}
                    </td>
                    <td className="px-4 py-3 text-right text-slate-400">
                      {player.age || '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Info Box */}
      <div className="mt-6 p-4 bg-slate-900/80 border border-slate-700 rounded-lg">
        <h3 className="font-semibold text-white mb-2">About Elo Ratings</h3>
        <p className="text-sm text-slate-400">
          Elo ratings from Tennis Abstract provide an alternative ranking system based on 
          a player's performance rather than tournament results. A higher Elo indicates 
          a stronger player based on head-to-head match outcomes and the quality of opponents.
        </p>
      </div>
    </div>
  );
}
