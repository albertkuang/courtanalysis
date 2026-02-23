import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
  Trophy, Calendar, Users, ChevronRight, ChevronDown, 
  Loader2, RefreshCw, Search, Filter, ArrowLeft
} from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8004';

// Tournament colors
const tournamentColors = {
  'Australian Open': { bg: 'bg-green-500/20', text: 'text-green-400', border: 'border-green-500/40' },
  'French Open': { bg: 'bg-red-500/20', text: 'text-red-400', border: 'border-red-500/40' },
  'Wimbledon': { bg: 'bg-emerald-500/20', text: 'text-emerald-400', border: 'border-emerald-500/40' },
  'US Open': { bg: 'bg-blue-500/20', text: 'text-blue-400', border: 'border-blue-500/40' },
};

// Round order for sorting
const roundOrder = {
  'R128': 1, 'R64': 2, 'R32': 3, 'R16': 4, 'QF': 5, 'SF': 6, 'F': 7, 'BR': 8
};

// SlamPointByPoint Main Component
const SlamPointByPoint = ({ onPlayerClick }) => {
  const [loading, setLoading] = useState(true);
  const [matches, setMatches] = useState([]);
  const [stats, setStats] = useState(null);
  const [selectedMatch, setSelectedMatch] = useState(null);
  const [matchDetail, setMatchDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState(null);
  const [debugInfo, setDebugInfo] = useState('');
  
  // Filters
  const [selectedTournament, setSelectedTournament] = useState('all');
  const [selectedYear, setSelectedYear] = useState('all');
  const [selectedRound, setSelectedRound] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');

  // Fetch matches on mount and when filters change
  useEffect(() => {
    fetchMatches();
    fetchStats();
  }, []);

  // Refetch when filters change
  useEffect(() => {
    fetchMatches();
  }, [selectedTournament, selectedYear, selectedRound]);

  const fetchMatches = async () => {
    setLoading(true);
    setDebugInfo('Starting fetch...');
    try {
      const params = new URLSearchParams();
      if (selectedTournament !== 'all') params.append('tournament', selectedTournament);
      if (selectedYear !== 'all') params.append('year', selectedYear);
      if (selectedRound !== 'all') params.append('round', selectedRound);
      params.append('limit', '100');
      
      const url = `${API_BASE}/slam/matches?${params}`;
      setDebugInfo(`Fetching: ${url}`);
      console.log('Fetching slam matches from:', url);
      
      const response = await axios.get(url);
      let data = response.data.data || [];
      
      // Filter by search term
      if (searchTerm) {
        const term = searchTerm.toLowerCase();
        data = data.filter(m => 
          m.winner_name?.toLowerCase().includes(term) || 
          m.loser_name?.toLowerCase().includes(term)
        );
      }
      
      // Sort by year (desc), then round
      data.sort((a, b) => {
        if (a.year !== b.year) return b.year - a.year;
        return (roundOrder[a.round] || 0) - (roundOrder[b.round] || 0);
      });
      
      setMatches(data);
    } catch (error) {
      console.error('Error fetching slam matches:', error);
      setError('Failed to connect to API server. Make sure the backend is running on port 8004.');
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const response = await axios.get(`${API_BASE}/slam/stats/overview`);
      setStats(response.data);
    } catch (error) {
      console.error('Error fetching slam stats:', error);
    }
  };

  const fetchMatchDetail = async (matchId) => {
    setDetailLoading(true);
    try {
      const response = await axios.get(`${API_BASE}/slam/matches/${matchId}`);
      setMatchDetail(response.data);
    } catch (error) {
      console.error('Error fetching match detail:', error);
    } finally {
      setDetailLoading(false);
    }
  };

  const handleMatchClick = (match) => {
    setSelectedMatch(match);
    fetchMatchDetail(match.match_id);
  };

  const handleBack = () => {
    setSelectedMatch(null);
    setMatchDetail(null);
  };

  // Extract unique values for filters
  const years = [...new Set(matches.map(m => m.year).filter(Boolean))].sort((a, b) => b - a);
  const rounds = ['R128', 'R64', 'R32', 'R16', 'QF', 'SF', 'F'];
  const tournaments = ['Australian Open', 'French Open', 'Wimbledon', 'US Open'];

  // If viewing a specific match
  if (selectedMatch && matchDetail) {
    return (
      <SlamMatchDetail 
        match={selectedMatch} 
        detail={matchDetail} 
        loading={detailLoading}
        onBack={handleBack}
      />
    );
  }

  return (
    <div className="h-full flex flex-col animate-in fade-in duration-300">
      {/* Header */}
      <div className="p-4 border-b border-slate-800 bg-slate-900/50 backdrop-blur">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <Trophy className="w-6 h-6 text-amber-400" />
            <h2 className="text-xl font-bold text-white">Grand Slam Point-by-Point</h2>
          </div>
          <button 
            onClick={fetchMatches} 
            className="p-2 hover:bg-slate-800 rounded-lg transition-colors"
            title="Refresh"
          >
            <RefreshCw className={`w-4 h-4 text-slate-400 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>

        {/* Stats Overview */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
            {stats.matches_by_tournament?.slice(0, 4).map((stat, idx) => (
              <div key={idx} className={`p-3 rounded-lg border ${tournamentColors[stat.tournament]?.bg || 'bg-slate-800/50'} ${tournamentColors[stat.tournament]?.border || 'border-slate-700'}`}>
                <div className="text-xs text-slate-400 truncate">{stat.tournament}</div>
                <div className={`font-bold ${tournamentColors[stat.tournament]?.text || 'text-white'}`}>
                  {stat.count} matches
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Error Message */}
        {error && (
          <div className="mb-4 p-3 bg-red-500/20 border border-red-500/40 rounded-lg">
            <p className="text-red-400 text-sm">{error}</p>
            <button onClick={() => setError(null)} className="text-red-300 text-xs underline mt-1">Dismiss</button>
          </div>
        )}

        {/* Debug Info */}
        {debugInfo && (
          <div className="mb-4 p-3 bg-yellow-500/20 border border-yellow-500/40 rounded-lg">
            <p className="text-yellow-400 text-xs font-mono">{debugInfo}</p>
          </div>
        )}

        {/* Filters */}
        <div className="flex flex-wrap gap-3">
          <select
            value={selectedTournament}
            onChange={(e) => setSelectedTournament(e.target.value)}
            className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-tennis-blue"
          >
            <option value="all">All Tournaments</option>
            {tournaments.map(t => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>

          <select
            value={selectedYear}
            onChange={(e) => setSelectedYear(e.target.value)}
            className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-tennis-blue"
          >
            <option value="all">All Years</option>
            {years.map(y => (
              <option key={y} value={y}>{y}</option>
            ))}
          </select>

          <select
            value={selectedRound}
            onChange={(e) => setSelectedRound(e.target.value)}
            className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-tennis-blue"
          >
            <option value="all">All Rounds</option>
            {rounds.map(r => (
              <option key={r} value={r}>{r}</option>
            ))}
          </select>

          <div className="flex-1 min-w-[200px]">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <input
                type="text"
                placeholder="Search players..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && fetchMatches()}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg pl-10 pr-3 py-2 text-sm text-white placeholder-slate-400 focus:outline-none focus:border-tennis-blue"
              />
            </div>
          </div>
        </div>
      </div>

      {/* Matches List */}
      <div className="flex-1 overflow-y-auto p-4">
        {loading ? (
          <div className="flex justify-center items-center h-64">
            <Loader2 className="w-8 h-8 text-tennis-blue animate-spin" />
          </div>
        ) : matches.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64 text-slate-400">
            <Trophy className="w-12 h-12 mb-4 opacity-50" />
            <p>No matches found</p>
            <p className="text-sm mt-1">Try adjusting your filters</p>
          </div>
        ) : (
          <div className="space-y-2">
            {matches.map((match) => (
              <div
                key={match.match_id}
                onClick={() => handleMatchClick(match)}
                className="bg-slate-900 border border-slate-800 rounded-xl p-4 hover:border-amber-500/50 cursor-pointer transition-all hover:bg-slate-800/50"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    {/* Tournament Badge */}
                    <span className={`px-2 py-1 rounded text-xs font-semibold border ${tournamentColors[match.tournament]?.bg || 'bg-slate-800'} ${tournamentColors[match.tournament]?.text || 'text-slate-300'} ${tournamentColors[match.tournament]?.border || 'border-slate-700'}`}>
                      {match.tournament?.substring(0, 2)}
                    </span>
                    
                    {/* Round */}
                    <span className="text-xs text-slate-500 font-medium">
                      {match.round}
                    </span>
                    
                    {/* Year */}
                    <span className="text-xs text-slate-500">
                      {match.year}
                    </span>
                  </div>
                  
                  <ChevronRight className="w-4 h-4 text-slate-500" />
                </div>

                {/* Players & Score */}
                <div className="mt-3 flex items-center justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-white font-medium">{match.winner_name}</span>
                      {match.winner_seed && <span className="text-xs text-slate-500">({match.winner_seed})</span>}
                    </div>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-slate-400">{match.loser_name}</span>
                      {match.loser_seed && <span className="text-xs text-slate-500">({match.loser_seed})</span>}
                    </div>
                  </div>
                  
                  <div className="text-right">
                    <div className="text-amber-400 font-bold">{match.score}</div>
                    {match.match_duration && (
                      <div className="text-xs text-slate-500 mt-1">
                        {Math.floor(match.match_duration / 60)}h {match.match_duration % 60}m
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

// Match Detail Component - Shows point-by-point breakdown
const SlamMatchDetail = ({ match, detail, loading, onBack }) => {
  const [expandedSet, setExpandedSet] = useState(1);
  const [showAllPoints, setShowAllPoints] = useState(false);

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-tennis-blue animate-spin" />
      </div>
    );
  }

  const points = detail.points || [];
  const displayPoints = showAllPoints ? points : points.slice(0, 50);

  // Group points by set
  const pointsBySet = {};
  points.forEach(p => {
    const setKey = p.set_num || 1;
    if (!pointsBySet[setKey]) pointsBySet[setKey] = [];
    pointsBySet[setKey].push(p);
  });

  // Calculate set scores
  const getSetScore = (setPoints) => {
    const serverGames = new Set();
    const receiverGames = new Set();
    
    setPoints.forEach(p => {
      const serverScore = p.server_score;
      const receiverScore = p.receiver_score;
      
      // Check for game win (score goes to 40+ or advantage)
      if (serverScore === 'G' || (serverScore > receiverScore && receiverScore >= 40)) {
        serverGames.add(p.game_num);
      }
      if (receiverScore === 'G' || (receiverScore > serverScore && serverScore >= 40)) {
        receiverGames.add(p.game_num);
      }
    });
    
    return { server: serverGames.size, receiver: receiverGames.size };
  };

  return (
    <div className="h-full flex flex-col animate-in fade-in duration-300">
      {/* Header with back button */}
      <div className="p-4 border-b border-slate-800 bg-slate-900/50 backdrop-blur">
        <button
          onClick={onBack}
          className="flex items-center gap-2 text-slate-400 hover:text-white transition-colors mb-3"
        >
          <ArrowLeft className="w-4 h-4" />
          <span className="text-sm">Back to matches</span>
        </button>

        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className={`px-2 py-1 rounded text-xs font-semibold border ${tournamentColors[match.tournament]?.bg || 'bg-slate-800'} ${tournamentColors[match.tournament]?.text || 'text-slate-300'} ${tournamentColors[match.tournament]?.border || 'border-slate-700'}`}>
                {match.tournament}
              </span>
              <span className="text-xs text-slate-500">{match.year} - {match.round}</span>
            </div>
            <h2 className="text-xl font-bold text-white">
              {match.winner_name} vs {match.loser_name}
            </h2>
            <div className="text-amber-400 font-semibold mt-1">
              {match.score} • {match.winner_name} won
            </div>
          </div>
          
          <div className="text-right text-sm text-slate-400">
            <div>{detail.points_count?.toLocaleString()} total points</div>
            {match.match_duration && (
              <div>{Math.floor(match.match_duration / 60)}h {match.match_duration % 60}m</div>
            )}
          </div>
        </div>
      </div>

      {/* Points List */}
      <div className="flex-1 overflow-y-auto p-4">
        <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
          <div className="p-3 border-b border-slate-800 bg-slate-800/50">
            <h3 className="font-semibold text-white">Point-by-Point Breakdown</h3>
          </div>
          
          {points.length === 0 ? (
            <div className="p-8 text-center text-slate-400">
              No point data available for this match
            </div>
          ) : (
            <div className="divide-y divide-slate-800">
              {displayPoints.map((point, idx) => (
                <PointRow key={idx} point={point} pointNum={idx + 1} />
              ))}
            </div>
          )}
          
          {points.length > 50 && !showAllPoints && (
            <div className="p-3 border-t border-slate-800 text-center">
              <button
                onClick={() => setShowAllPoints(true)}
                className="text-tennis-blue hover:underline text-sm"
              >
                Show all {points.length} points
              </button>
            </div>
          )}
          
          {showAllPoints && points.length > 50 && (
            <div className="p-3 border-t border-slate-800 text-center">
              <button
                onClick={() => setShowAllPoints(false)}
                className="text-slate-400 hover:text-white text-sm"
              >
                Show less
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// Individual Point Row Component
const PointRow = ({ point, pointNum }) => {
  const isServerWinner = point.winner_of_point === 'S';
  const serverName = 'Server'; // We don't have player names in points data
  const receiverName = 'Receiver';
  
  // Determine point outcome
  let outcome = '';
  if (point.serve_return_winner) outcome = 'Winner';
  else if (point.serve_return_error) outcome = 'Error';
  else if (point.rally_count && point.rally_count > 8) outcome = 'Rally';
  
  return (
    <div className="p-3 hover:bg-slate-800/30 transition-colors">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          {/* Point Number */}
          <span className="text-xs text-slate-500 w-8">{pointNum}</span>
          
          {/* Set/Game/Point Score */}
          <div className="flex items-center gap-2">
            <span className="text-xs bg-slate-800 px-1.5 py-0.5 rounded text-slate-400">
              {point.set_num}-{point.game_num}
            </span>
            <span className="text-sm font-mono text-white">
              {point.server_score}-{point.receiver_score}
            </span>
          </div>
        </div>
        
        {/* Outcome */}
        <div className="flex items-center gap-2">
          {point.rally_count > 0 && (
            <span className="text-xs text-slate-500">
              {point.rally_count} shots
            </span>
          )}
          <span className={`text-xs px-2 py-0.5 rounded ${
            isServerWinner 
              ? 'bg-amber-500/20 text-amber-400' 
              : 'bg-blue-500/20 text-blue-400'
          }`}>
            {isServerWinner ? 'S' : 'R'} won
          </span>
        </div>
      </div>
      
      {/* Serve Details */}
      {point.serve_num && (
        <div className="mt-1 ml-11 text-xs text-slate-500">
          {point.serve_num === 1 ? '1st' : '2nd'} serve
          {point.serve_width && ` • ${point.serve_width}`}
          {point.serve_depth && ` • ${point.serve_depth}`}
        </div>
      )}
    </div>
  );
};

export default SlamPointByPoint;
