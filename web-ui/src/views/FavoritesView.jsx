import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
    Star, Loader2, Users, RefreshCw, Calendar, TrendingUp, TrendingDown, Trash2
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const FavoritesView = ({ onPlayerClick }) => {
    const { user } = useAuth();
    const [favorites, setFavorites] = useState([]);
    const [feed, setFeed] = useState([]);
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState('players');

    useEffect(() => {
        if (user) {
            fetchFavorites();
            fetchFeed();
        } else {
            setLoading(false);
        }
    }, [user]);

    const fetchFavorites = async () => {
        setLoading(true);
        try {
            const res = await axios.get('/api/users/favorites');
            setFavorites(res.data.data || []);
        } catch (err) {
            console.error('Error fetching favorites:', err);
        }
        setLoading(false);
    };

    const fetchFeed = async () => {
        try {
            const res = await axios.get('/api/users/favorites/feed', { params: { limit: 50 } });
            setFeed(res.data.data || []);
        } catch (err) {
            console.error('Error fetching favorites feed:', err);
        }
    };

    const removeFavorite = async (playerId) => {
        try {
            await axios.delete(`/api/users/favorites/${playerId}`);
            setFavorites(favorites.filter(f => f.player_id !== playerId));
        } catch (err) {
            console.error('Error removing favorite:', err);
        }
    };

    if (!user) {
        return (
            <div className="h-full flex flex-col items-center justify-center text-slate-500 p-8">
                <Star className="w-16 h-16 mb-4 opacity-20" />
                <h2 className="text-xl font-bold text-white mb-2">Sign in to View Favorites</h2>
                <p className="text-sm text-center max-w-md">
                    Save your favorite players and get updates on their recent matches and rating changes.
                </p>
            </div>
        );
    }

    return (
        <div className="h-full flex flex-col animate-in fade-in duration-300">
            {/* Header */}
            <div className="p-4 md:p-6 border-b border-slate-800 bg-slate-900/50 backdrop-blur shrink-0">
                <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-3">
                        <Star className="w-6 h-6 text-amber-400" />
                        <div>
                            <h1 className="text-xl font-bold text-white">Favorites</h1>
                            <p className="text-xs text-slate-500 mt-0.5">{favorites.length} tracked players</p>
                        </div>
                    </div>
                    <button
                        onClick={() => { fetchFavorites(); fetchFeed(); }}
                        disabled={loading}
                        className="flex items-center gap-2 px-3 py-2 bg-amber-500/10 text-amber-400 rounded-lg hover:bg-amber-500/20 transition-colors text-sm"
                    >
                        <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                        Refresh
                    </button>
                </div>

                {/* Tabs */}
                <div className="flex gap-2">
                    <button
                        onClick={() => setActiveTab('players')}
                        className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${activeTab === 'players'
                            ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                            : 'bg-slate-800 text-slate-400 hover:text-white border border-slate-700'
                            }`}
                    >
                        <Users className="w-4 h-4 inline mr-2" />Players
                    </button>
                    <button
                        onClick={() => setActiveTab('feed')}
                        className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${activeTab === 'feed'
                            ? 'bg-tennis-blue/20 text-tennis-blue border border-tennis-blue/30'
                            : 'bg-slate-800 text-slate-400 hover:text-white border border-slate-700'
                            }`}
                    >
                        <Calendar className="w-4 h-4 inline mr-2" />Activity Feed
                    </button>
                </div>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-4 md:p-6">
                {loading ? (
                    <div className="flex flex-col items-center justify-center h-64">
                        <Loader2 className="w-8 h-8 text-amber-400 animate-spin" />
                        <span className="mt-3 text-slate-400 text-sm">Loading favorites...</span>
                    </div>
                ) : activeTab === 'players' ? (
                    favorites.length === 0 ? (
                        <div className="flex flex-col items-center justify-center h-64 text-slate-500">
                            <Star className="w-12 h-12 mb-4 opacity-20" />
                            <p>No favorites yet</p>
                            <p className="text-sm mt-1">Click the star icon on any player to add them here</p>
                        </div>
                    ) : (
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                            {favorites.map(player => (
                                <div
                                    key={player.player_id}
                                    className="bg-slate-900 border border-slate-800 rounded-xl p-4 hover:border-amber-500/50 transition-all cursor-pointer group"
                                    onClick={() => onPlayerClick && onPlayerClick(player)}
                                >
                                    <div className="flex items-start justify-between">
                                        <div>
                                            <h3 className="font-bold text-white group-hover:text-amber-400 transition-colors">{player.name}</h3>
                                            <div className="flex items-center gap-2 mt-1 text-sm text-slate-400">
                                                <span>{player.country || '—'}</span>
                                                {player.age && <span>• Age {player.age}</span>}
                                            </div>
                                        </div>
                                        <button
                                            onClick={(e) => { e.stopPropagation(); removeFavorite(player.player_id); }}
                                            className="p-1.5 rounded-lg hover:bg-rose-500/20 text-slate-500 hover:text-rose-400 transition-all opacity-0 group-hover:opacity-100"
                                            title="Remove from favorites"
                                        >
                                            <Trash2 className="w-4 h-4" />
                                        </button>
                                    </div>
                                    <div className="mt-3 flex items-center gap-4">
                                        <div>
                                            <div className="text-xs text-slate-500">UTR Singles</div>
                                            <div className="text-lg font-bold text-emerald-400 font-mono">{player.utr_singles?.toFixed(2) || '—'}</div>
                                        </div>
                                        {player.year_delta !== undefined && player.year_delta !== null && (
                                            <div>
                                                <div className="text-xs text-slate-500">Year Δ</div>
                                                <div className={`text-sm font-bold flex items-center gap-1 ${player.year_delta > 0 ? 'text-emerald-400' : player.year_delta < 0 ? 'text-rose-400' : 'text-slate-400'}`}>
                                                    {player.year_delta > 0 ? <TrendingUp className="w-3 h-3" /> : player.year_delta < 0 ? <TrendingDown className="w-3 h-3" /> : null}
                                                    {player.year_delta > 0 ? '+' : ''}{player.year_delta?.toFixed(2)}
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            ))}
                        </div>
                    )
                ) : (
                    /* Activity Feed */
                    feed.length === 0 ? (
                        <div className="flex flex-col items-center justify-center h-64 text-slate-500">
                            <Calendar className="w-12 h-12 mb-4 opacity-20" />
                            <p>No recent activity from your favorites</p>
                        </div>
                    ) : (
                        <div className="space-y-3">
                            {feed.map((item, idx) => (
                                item.type === 'news' ? (
                                    <div key={idx} className="bg-slate-900 border border-slate-800 rounded-xl p-4">
                                        <div className="flex items-start gap-4">
                                            <div className="w-10 h-10 rounded-full bg-blue-500/10 flex items-center justify-center shrink-0">
                                                <Calendar className="w-5 h-5 text-blue-400" />
                                            </div>
                                            <div className="flex-1">
                                                <div className="flex items-center justify-between">
                                                    <div className="flex items-center gap-2 mb-1">
                                                        <span
                                                            className="font-bold text-white cursor-pointer hover:text-tennis-blue"
                                                            onClick={() => onPlayerClick && onPlayerClick({ player_id: item.player_id_ref, name: item.player_name })}
                                                        >
                                                            {item.player_name}
                                                        </span>
                                                        <span className="text-xs bg-slate-800 px-1.5 py-0.5 rounded text-slate-400">News</span>
                                                    </div>
                                                    <span className="text-xs text-slate-500 whitespace-nowrap ml-2">
                                                        {item.timestamp ? new Date(item.timestamp).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' }) : ''}
                                                    </span>
                                                </div>
                                                <h4 className="text-sm font-medium text-slate-200">{item.title}</h4>
                                                {item.summary && (
                                                    <p className="text-xs text-slate-400 mt-1 line-clamp-2">{item.summary}</p>
                                                )}
                                                <div className="flex items-center gap-3 mt-2">
                                                    {item.source && <span className="text-[10px] text-slate-500 uppercase font-semibold">{item.source}</span>}
                                                    {item.url && (
                                                        <a href={item.url} target="_blank" rel="noreferrer" className="text-xs text-tennis-blue hover:underline">
                                                            Read more
                                                        </a>
                                                    )}
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                ) : (
                                    <div key={idx} className="bg-slate-900 border border-slate-800 rounded-xl p-4">
                                        <div className="flex items-center justify-between">
                                            <div className="flex items-center gap-2">
                                                <span className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold ${item.result === 'W' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'
                                                    }`}>
                                                    {item.result}
                                                </span>
                                                <span
                                                    className="font-medium text-white cursor-pointer hover:text-tennis-blue transition-colors"
                                                    onClick={() => onPlayerClick && onPlayerClick({ player_id: item.player_id, name: item.player_name })}
                                                >
                                                    {item.player_name || 'Unknown'}
                                                </span>
                                                <span className="text-slate-500">vs</span>
                                                {item.opponent_id ? (
                                                    <span
                                                        className="text-slate-300 hover:text-tennis-blue cursor-pointer transition-colors"
                                                        onClick={() => onPlayerClick && onPlayerClick({ player_id: item.opponent_id, name: item.opponent_name })}
                                                    >
                                                        {item.opponent_name || 'Unknown'}
                                                    </span>
                                                ) : (
                                                    <span className="text-slate-300">{item.opponent_name || 'Unknown'}</span>
                                                )}
                                            </div>
                                            <span className="text-xs text-slate-500 ml-2 whitespace-nowrap">
                                                {item.timestamp ? new Date(item.timestamp).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' }) : ''}
                                            </span>
                                        </div>
                                        {item.score && (
                                            <div className="mt-1 text-sm text-amber-400 font-medium">{item.score}</div>
                                        )}
                                        {item.tournament && (
                                            <div className="mt-1 text-xs text-slate-500">{item.tournament}</div>
                                        )}
                                    </div>
                                )
                            ))}
                        </div>
                    )
                )}
            </div>
        </div>
    );
};

export default FavoritesView;
