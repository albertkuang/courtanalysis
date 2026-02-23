import React, { useState, useEffect, useMemo } from 'react';
import axios from 'axios';
import { Routes, Route, Navigate, useNavigate, useLocation } from 'react-router-dom';
import {
  Trophy, Search, Users, Activity, TrendingUp, ChevronRight,
  MapPin, Calendar, ExternalLink, X, ArrowUpDown, Menu, Lightbulb, TrendingDown,
  FileText, Download, Loader2, LogOut, User as UserIcon, Cpu, Star, Newspaper, BarChart3, ChevronDown,
  GraduationCap, History

} from 'lucide-react';

// Shared & Layout Components
import { SelectFilter, SortableHeader, StatBadge } from './components/shared';
import { BrandHeader, NavMenu, MobileNavItem } from './components/layout';
import {
  PlayerHeader,
  RatingChart,
  WinLossDonut,
  ClutchRadar,
  AdvancedAnalysis,
  HeadToHeadSection,
  MatchLog,
  CareerTimeline,
  PlayerSocialFeed
} from './components/player';
import LoginModal from './components/LoginModal';

// View Components
import ScoutView from './views/ScoutView';
import MatchHistoryView from './views/MatchHistoryView';
import UTRHistoryView from './views/UTRHistoryView';
import PlayerInsightsView from './views/PlayerInsightsView';
import { OpponentsView, SocialMediaSection } from './views/OpponentsView';
import { GamePlanView, QuarterlyReviewView, RecruitView } from './views/AIPlayerViews';
import InsightsView from './views/InsightsView';
import ReportView from './views/ReportView';
import ComparisonView from './views/ComparisonView';
import OngoingTournamentsView from './components/OngoingTournamentsView';
import RecentMatchesView from './views/RecentMatchesView';
import FavoritesView from './views/FavoritesView';
import NewsPulseView from './views/NewsPulseView';
import TournamentHistoryView from './views/TournamentHistoryView';
import ITFJuniorAnalysisView from './views/ITFJuniorAnalysisView';

// Existing Feature Components (already built, now routed)
import StatsExplorer from './components/StatsExplorer';
import TennisAbstractElo from './components/TennisAbstractElo';
import SlamPointByPoint from './components/SlamPointByPoint';
import CollegeScout from './components/CollegeScout';
import AdvancedStats from './components/AdvancedStats';

// Auth Context
import { useAuth } from './context/AuthContext';

function App() {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, login, logout } = useAuth();

  // Data States
  const [players, setPlayers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [matchHistory, setMatchHistory] = useState([]);
  const [ratingHistory, setRatingHistory] = useState([]);
  const [advancedData, setAdvancedData] = useState(null);
  const [isFavorite, setIsFavorite] = useState(false);

  // Match history pagination
  const [matchPagination, setMatchPagination] = useState({
    total: 0,
    limit: 100,
    offset: 0,
    year: null, // null means all years
    availableYears: [], // years with matches for this player
    stats: null // Aggregated stats
  });

  // Filters
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('junior');
  const [country, setCountry] = useState('ALL');
  const [gender, setGender] = useState('M');
  const [minUtr, setMinUtr] = useState(0);

  // UI States
  const [selectedPlayer, setSelectedPlayer] = useState(null);
  const [compareList, setCompareList] = useState([]);
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [activeTab, setActiveTab] = useState('overview');
  const [sortConfig, setSortConfig] = useState({ key: 'utr_singles', direction: 'desc' });

  // Map view for NavMenu compatibility (if we don't fully refactor NavMenu right now)
  const currentView = useMemo(() => {
    const path = location.pathname.substring(1) || 'scout';
    return path;
  }, [location.pathname]);

  const setView = (v) => {
    navigate(`/${v}`);
  };

  useEffect(() => {
    fetchPlayers();
  }, [search, category, country, gender]);

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

  // Analysis request controller for cancellation
  let analysisController = null;

  const fetchPlayerDetails = async (id) => {
    try {
      // Cancel any pending analysis request from previous player
      if (analysisController) {
        analysisController.abort();
      }

      // Load essential data (player detail, matches, history, favorite) - fast
      const [playerRes, matchesRes, historyRes, favRes] = await Promise.all([
        axios.get(`/api/players/${id}`).catch(err => { console.error("Player fetch failed", err); return { data: {} }; }),
        axios.get(`/api/players/${id}/matches`, {
          params: {
            limit: matchPagination.limit,
            offset: matchPagination.offset,
            year: matchPagination.year
          }
        }).catch(err => { console.error("Matches fetch failed", err); return { data: { data: [], total: 0 } }; }),
        axios.get(`/api/players/${id}/history`).catch(err => { console.error("History fetch failed", err); return { data: { data: [] } }; }),
        axios.get(`/api/players/${id}/is_favorite`).catch(err => { console.error("Favorite check failed", err); return { data: { is_favorite: false } }; })
      ]);

      // Update selected player with fresh data from API
      if (playerRes.data && playerRes.data.player_id) {
        setSelectedPlayer(playerRes.data);
      }

      setMatchHistory(matchesRes.data.data || []);
      setMatchPagination(prev => ({
        ...prev,
        total: matchesRes.data.total || 0,
        availableYears: matchesRes.data.available_years || [],
        stats: matchesRes.data.stats || null
      }));
      setRatingHistory(historyRes.data.data || []);
      setIsFavorite(favRes.data.is_favorite);
      setAdvancedData(null); // Clear previous analysis

    } catch (err) {
      console.error(err);
      setMatchHistory([]);
      setRatingHistory([]);
      setAdvancedData(null);
    }
  };

  // Load analysis on demand (when Analysis tab is clicked)
  const loadAnalysis = async (id) => {
    if (analysisController) {
      analysisController.abort();
    }
    analysisController = new AbortController();

    try {
      const res = await axios.get(`/api/players/${id}/analysis`, { signal: analysisController.signal });
      setAdvancedData(res.data.data || null);
    } catch (err) {
      if (err.name !== 'CanceledError' && err.name !== 'AbortError') {
        console.error("Analysis fetch failed", err);
      }
      setAdvancedData(null);
    }
  };

  // Fetch matches with pagination
  const fetchMatchHistory = async (id, year = null, offset = 0, limit = 100) => {
    try {
      const res = await axios.get(`/api/players/${id}/matches`, {
        params: { year, offset, limit }
      });
      setMatchHistory(res.data.data || []);
      setMatchPagination({
        total: res.data.total || 0,
        limit,
        offset,
        year,
        availableYears: res.data.available_years || [],
        stats: res.data.stats || null
      });
    } catch (err) {
      console.error("Failed to fetch match history:", err);
    }
  };

  const handlePlayerClick = (player) => {
    setSelectedPlayer(player);
    setActiveTab('overview');
    fetchPlayerDetails(player.player_id);
  };

  const addToCompare = (player) => {
    if (compareList.find(p => p.player_id === player.player_id)) return;
    const newList = compareList.length >= 2 ? [compareList[0], player] : [...compareList, player];
    setCompareList(newList);
    navigate('/compare');
  };

  const handleSort = (key) => {
    let direction = 'desc';
    if (sortConfig.key === key && sortConfig.direction === 'desc') {
      direction = 'asc';
    }
    setSortConfig({ key, direction });
  };

  const toggleFavorite = async (playerId) => {
    if (!user) {
      setShowAuthModal(true);
      return;
    }
    try {
      const response = await axios.post(`/api/players/${playerId}/favorite`);
      if (response.data.action === 'added') setIsFavorite(true);
      else setIsFavorite(false);
    } catch (err) {
      console.error("Toggle favorite failed", err);
    }
  };

  const tabs = [
    { id: 'overview', label: 'Overview', icon: <Activity className="w-4 h-4" /> },
    { id: 'matchhistory', label: 'Match History', icon: <Calendar className="w-4 h-4" /> },
    { id: 'utrhistory', label: 'UTR History', icon: <History className="w-4 h-4" /> },
    { id: 'opponents', label: 'Opponents', icon: <Users className="w-4 h-4" /> },
    { id: 'playerinsights', label: 'Insights', icon: <Lightbulb className="w-4 h-4" /> },
    { id: 'social', label: 'Social', icon: <Newspaper className="w-4 h-4 text-pink-400" /> },
    { id: 'gameplan', label: 'Game Plan', icon: <Cpu className="w-4 h-4 text-emerald-400" /> },
    { id: 'review', label: 'Review', icon: <TrendingUp className="w-4 h-4 text-tennis-blue" /> },
    { id: 'recruiting', label: 'Recruiting', icon: <GraduationCap className="w-4 h-4 text-indigo-400" /> }
  ];

  return (
    <div className="flex flex-col md:flex-row h-screen bg-tennis-dark text-slate-200 overflow-hidden font-sans">

      {/* DESKTOP SIDEBAR */}
      <div className="hidden md:flex w-64 bg-slate-900 border-r border-slate-800 p-4 flex-col">
        <BrandHeader user={user} onLogout={logout} onLoginClick={() => setShowAuthModal(true)} />
        <NavMenu
          view={currentView}
          setView={setView}
          category={category}
          setCategory={setCategory}
          setCountry={setCountry}
          setMinUtr={setMinUtr}
          gender={gender}
        />
        <div className="text-[10px] text-slate-700 mt-auto pt-4 border-t border-slate-800 font-mono flex justify-between items-center">
          <span>COURTSIDE v2.5</span>
          <span className="text-tennis-green">Live Ops</span>
        </div>
      </div>

      {/* MOBILE HEADER */}
      <div className="md:hidden h-14 bg-slate-900 border-b border-slate-800 flex items-center px-4 justify-between shrink-0">
        <BrandHeader small user={user} onLogout={logout} onLoginClick={() => setShowAuthModal(true)} />
        <div className="flex gap-2">
          <StatBadge label="Live" value={players?.length || 0} small />
        </div>
      </div>

      {/* MAIN CONTENT AREA */}
      <div className="flex-1 flex flex-col min-w-0 bg-tennis-dark relative">
        <Routes>
          <Route path="/" element={<Navigate to="/scout" replace />} />
          <Route path="/scout" element={
            <ScoutView
              players={players}
              loading={loading}
              search={search}
              setSearch={setSearch}
              country={country}
              setCountry={setCountry}
              gender={gender}
              setGender={setGender}
              category={category}
              setCategory={setCategory}
              sortConfig={sortConfig}
              handleSort={handleSort}
              handlePlayerClick={handlePlayerClick}
              selectedPlayerId={selectedPlayer?.player_id}
              addToCompare={addToCompare}
              toggleFavorite={toggleFavorite}
              user={user}
            />
          } />
          <Route path="/insights" element={
            <InsightsView
              players={players}
              minUtr={minUtr}
              setMinUtr={setMinUtr}
              country={country}
              setCountry={setCountry}
              gender={gender}
              setGender={setGender}
              category={category}
              setCategory={setCategory}
              onPlayerClick={handlePlayerClick}
            />
          } />
          <Route path="/report" element={<ReportView />} />
          <Route path="/compare" element={
            <ComparisonView
              list={compareList}
              onRemove={(id) => setCompareList(compareList.filter(c => c.player_id !== id))}
            />
          } />
          <Route path="/tournaments" element={<OngoingTournamentsView onPlayerClick={handlePlayerClick} />} />
          <Route path="/recent" element={
            <RecentMatchesView
              onPlayerClick={handlePlayerClick}
              country={country}
              gender={gender}
              category={category}
            />
          } />
          <Route path="/favorites" element={<FavoritesView onPlayerClick={handlePlayerClick} />} />
          <Route path="/news" element={<NewsPulseView />} />
          <Route path="/stats" element={<StatsExplorer />} />
          <Route path="/tennis_elo" element={<TennisAbstractElo onPlayerClick={handlePlayerClick} />} />
          <Route path="/slam_pbp" element={<SlamPointByPoint onPlayerClick={handlePlayerClick} />} />
          <Route path="/tournamenthistory" element={<TournamentHistoryView onPlayerClick={handlePlayerClick} />} />
          <Route path="/junioranalysis" element={<ITFJuniorAnalysisView onPlayerClick={handlePlayerClick} />} />
          <Route path="/college_scout" element={<CollegeScout onPlayerClick={handlePlayerClick} />} />
          <Route path="/advanced_analysis" element={<AdvancedStats currentPlayer={selectedPlayer} />} />
          <Route path="*" element={<div className="p-8 text-center text-slate-500">View coming soon...</div>} />
        </Routes>
      </div>

      {/* MOBILE BOTTOM NAV */}
      <div className="md:hidden fixed bottom-0 left-0 w-full bg-slate-900 border-t border-slate-800 flex justify-around p-2 z-40 pb-safe shadow-[0_-10px_30px_rgba(0,0,0,0.5)]">
        <MobileNavItem icon={<Users />} label="Scout" active={currentView === 'scout'} onClick={() => setView('scout')} />
        <MobileNavItem icon={<Lightbulb />} label="Insights" active={currentView === 'insights'} onClick={() => setView('insights')} />
        <MobileNavItem icon={<MapPin />} label="Tournaments" active={currentView === 'tournaments'} onClick={() => setView('tournaments')} />
        <MobileNavItem icon={<Activity />} label="Compare" active={currentView === 'compare'} onClick={() => setView('compare')} />
        <MobileNavItem icon={<Star />} label="Favorites" active={currentView === 'favorites'} onClick={() => setView('favorites')} />
      </div>

      {/* PLAYER DETAIL SLIDE-OVER */}
      {selectedPlayer && (
        <div className="fixed inset-0 z-50 flex justify-end bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="absolute inset-0" onClick={() => setSelectedPlayer(null)}></div>

          <div className="relative w-full md:w-[75vw] lg:w-[70vw] xl:w-[65vw] max-w-[1200px] h-full bg-slate-900 border-l border-slate-800 shadow-2xl flex flex-col animate-in slide-in-from-right duration-300">
            <button
              onClick={() => setSelectedPlayer(null)}
              className="absolute top-4 right-4 p-2.5 bg-slate-950/40 hover:bg-rose-500/20 text-white hover:text-rose-500 rounded-full transition-all z-10 border border-white/5"
            >
              <X className="w-5 h-5" />
            </button>

            <PlayerHeader
              player={selectedPlayer}
              isFavorite={isFavorite}
              onToggleFavorite={() => toggleFavorite(selectedPlayer.player_id)}
            />

            {/* TABS */}
            <div className="flex border-b border-slate-800 overflow-x-auto no-scrollbar bg-slate-900/50">
              {tabs.map(tab => (
                <button
                  key={tab.id}
                  onClick={() => {
                    setActiveTab(tab.id);
                    // Load analysis when Analysis tab is clicked
                    if (tab.id === 'review' && selectedPlayer) {
                      loadAnalysis(selectedPlayer.player_id);
                    }
                  }}
                  className={`flex items-center gap-2 px-6 py-4 text-xs font-bold uppercase tracking-widest whitespace-nowrap transition-all border-b-2 ${activeTab === tab.id
                    ? 'border-tennis-green text-white bg-white/5'
                    : 'border-transparent text-slate-500 hover:text-slate-300 hover:bg-white/5'
                    }`}
                >
                  {tab.icon} {tab.label}
                </button>
              ))}
            </div>

            {/* TAB CONTENT */}
            <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-6 pb-safe">
              {activeTab === 'overview' && (
                <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-300">
                  <CareerTimeline playerId={selectedPlayer.player_id} playerName={selectedPlayer.name} />

                  <div className="grid grid-cols-2 gap-4">
                    <WinLossDonut matches={matchHistory} playerId={selectedPlayer.player_id} />
                    <ClutchRadar player={selectedPlayer} matches={matchHistory} />
                  </div>

                  <AdvancedAnalysis data={advancedData} onPlayerClick={handlePlayerClick} />
                  <SocialMediaSection playerId={selectedPlayer.player_id} />
                  <HeadToHeadSection matches={matchHistory} playerId={selectedPlayer.player_id} />
                </div>
              )}

              {activeTab === 'matchhistory' && (
                <MatchHistoryView
                  matches={matchHistory}
                  playerId={selectedPlayer.player_id}
                  onPlayerClick={handlePlayerClick}
                  pagination={matchPagination}
                  onPageChange={(offset) => fetchMatchHistory(selectedPlayer.player_id, matchPagination.year, offset, matchPagination.limit)}
                  onYearChange={(year) => fetchMatchHistory(selectedPlayer.player_id, year, 0, matchPagination.limit)}
                />
              )}

              {activeTab === 'utrhistory' && (
                <UTRHistoryView history={ratingHistory} />
              )}

              {activeTab === 'opponents' && (
                <OpponentsView playerId={selectedPlayer.player_id} onPlayerClick={handlePlayerClick} />
              )}

              {activeTab === 'playerinsights' && (
                <PlayerInsightsView playerId={selectedPlayer.player_id} />
              )}

              {activeTab === 'gameplan' && (
                <GamePlanView playerId={selectedPlayer.player_id} playerName={selectedPlayer.name} />
              )}

              {activeTab === 'review' && (
                <QuarterlyReviewView playerId={selectedPlayer.player_id} playerName={selectedPlayer.name} />
              )}

              {activeTab === 'recruiting' && (
                <RecruitView playerId={selectedPlayer.player_id} playerName={selectedPlayer.name} playerAge={selectedPlayer.age} />
              )}

              {activeTab === 'social' && (
                <div className="animate-in fade-in slide-in-from-bottom-2 duration-300">
                  <PlayerSocialFeed playerId={selectedPlayer.player_id} playerName={selectedPlayer.name} />
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* AUTH MODAL */}
      {showAuthModal && (
        <LoginModal
          onClose={() => setShowAuthModal(false)}
          onLogin={(data) => {
            login(data.access_token, data.user);
            setShowAuthModal(false);
          }}
        />
      )}


    </div>
  );
}

export default App;
