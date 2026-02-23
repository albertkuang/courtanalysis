import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Loader2, Users, TrendingDown, TrendingUp, Activity, ExternalLink } from 'lucide-react';

// Opponents View Component
export const OpponentsView = ({ playerId, onPlayerClick }) => {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchData = async () => {
            if (!playerId) return;
            setLoading(true);
            try {
                const res = await axios.get(`/api/players/${playerId}/opponents`);
                setData(res.data.data);
            } catch (err) {
                console.error('Failed to fetch opponents:', err);
            }
            setLoading(false);
        };
        fetchData();
    }, [playerId]);

    if (loading) {
        return (
            <div className="flex justify-center items-center py-20">
                <Loader2 className="w-8 h-8 animate-spin text-tennis-blue" />
            </div>
        );
    }

    if (!data) {
        return <div className="text-center text-slate-500 py-10">No opponent data available.</div>;
    }

    const OpponentCard = ({ opponent, type }) => {
        const colorMap = {
            most: 'border-tennis-blue',
            lose: 'border-rose-500',
            win: 'border-emerald-500',
            close: 'border-amber-500'
        };
        const bgMap = {
            most: 'bg-tennis-blue/10',
            lose: 'bg-rose-500/10',
            win: 'bg-emerald-500/10',
            close: 'bg-amber-500/10'
        };

        return (
            <div
                className={`bg-slate-900 border ${colorMap[type]} rounded-xl p-4 cursor-pointer hover:scale-[1.02] transition-all duration-200 hover:shadow-lg`}
                onClick={() => onPlayerClick && onPlayerClick({ player_id: opponent.player_id, name: opponent.name })}
            >
                <div className="flex justify-between items-start mb-3">
                    <div className="flex-1 min-w-0">
                        <div className="font-bold text-white text-sm truncate">{opponent.name}</div>
                        <div className="text-[10px] text-slate-500">{opponent.country || 'Unknown'}</div>
                    </div>
                    <div className="text-right shrink-0 ml-2">
                        <div className="font-mono font-bold text-tennis-green text-sm">
                            {opponent.utr_singles?.toFixed(2) || '-'}
                        </div>
                        <div className="text-[10px] text-slate-500">UTR</div>
                    </div>
                </div>

                <div className={`${bgMap[type]} rounded-lg p-2 mb-3`}>
                    <div className="flex justify-between items-center">
                        <div className="text-center flex-1">
                            <div className="text-lg font-bold text-emerald-400">{opponent.wins}</div>
                            <div className="text-[10px] text-slate-400 uppercase">Wins</div>
                        </div>
                        <div className="text-slate-600 text-xs">vs</div>
                        <div className="text-center flex-1">
                            <div className="text-lg font-bold text-rose-400">{opponent.losses}</div>
                            <div className="text-[10px] text-slate-400 uppercase">Losses</div>
                        </div>
                    </div>
                </div>

                {opponent.matches && opponent.matches.length > 0 && (
                    <div className="space-y-1">
                        <div className="text-[10px] text-slate-500 uppercase font-bold mb-1">Recent Matches</div>
                        {opponent.matches.slice(0, 3).map((m, idx) => (
                            <div key={idx} className="flex justify-between items-center text-[10px] bg-slate-800/50 rounded px-2 py-1">
                                <span className={`font-bold ${m.won ? 'text-emerald-400' : 'text-rose-400'}`}>
                                    {m.won ? 'W' : 'L'}
                                </span>
                                <span className="text-slate-400 truncate flex-1 mx-2">{m.score}</span>
                                <span className="text-slate-500">{m.date?.split('T')[0]}</span>
                            </div>
                        ))}
                    </div>
                )}

                {opponent.last_match && (
                    <div className="text-[10px] text-slate-500 mt-2 pt-2 border-t border-slate-800">
                        Last: {opponent.last_match.split('T')[0]}
                    </div>
                )}
            </div>
        );
    };

    const Section = ({ title, icon, description, opponents, type, emptyText }) => (
        <div className="mb-8">
            <div className="flex items-center gap-2 mb-2">
                {icon}
                <h3 className="text-sm font-semibold text-white uppercase tracking-wider">{title}</h3>
            </div>
            <p className="text-xs text-slate-500 mb-4">{description}</p>
            {opponents.length > 0 ? (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
                    {opponents.map(opp => (
                        <OpponentCard key={opp.player_id} opponent={opp} type={type} />
                    ))}
                </div>
            ) : (
                <div className="text-center text-slate-600 py-6 bg-slate-900/50 rounded-xl border border-slate-800">
                    {emptyText}
                </div>
            )}
        </div>
    );

    return (
        <div className="animate-in fade-in duration-300">
            <Section
                title="Most Encountered"
                icon={<Users className="w-4 h-4 text-tennis-blue" />}
                description="Opponents faced most frequently"
                opponents={data.most_encountered || []}
                type="most"
                emptyText="No opponents with multiple matches"
            />

            <Section
                title="Dominators"
                icon={<TrendingDown className="w-4 h-4 text-rose-500" />}
                description="Always lost (3+ matches, 0 wins)"
                opponents={data.always_lose || []}
                type="lose"
                emptyText="No dominant opponents found (3+ matches with 0 wins required)"
            />

            <Section
                title="Dominated"
                icon={<TrendingUp className="w-4 h-4 text-emerald-500" />}
                description="Always won (3+ matches, 0 losses)"
                opponents={data.always_win || []}
                type="win"
                emptyText="No dominated opponents found (3+ matches with 0 losses required)"
            />

            <Section
                title="Closest Rivals"
                icon={<Activity className="w-4 h-4 text-amber-500" />}
                description="Most competitive matchups (4+ matches, closest to 50/50)"
                opponents={data.closest_matchups || []}
                type="close"
                emptyText="No close rivals found (4+ matches required)"
            />
        </div>
    );
};


// Social Media Section Component
export const SocialMediaSection = ({ playerId }) => {
    const [links, setLinks] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchLinks = async () => {
            setLoading(true);
            try {
                const res = await axios.get(`/api/players/${playerId}/social_media`);
                setLinks(res.data.data || []);
            } catch (err) {
                console.error('Failed to fetch social media links:', err);
                setLinks([]);
            }
            setLoading(false);
        };
        fetchLinks();
    }, [playerId]);

    const platformConfig = {
        instagram: { icon: '📸', color: 'bg-gradient-to-r from-purple-500 to-pink-500', label: 'Instagram' },
        twitter: { icon: '🐦', color: 'bg-sky-500', label: 'Twitter/X' },
        tiktok: { icon: '🎵', color: 'bg-black', label: 'TikTok' },
        youtube: { icon: '📺', color: 'bg-red-600', label: 'YouTube' },
        facebook: { icon: '📘', color: 'bg-blue-600', label: 'Facebook' },
        linkedin: { icon: '💼', color: 'bg-blue-700', label: 'LinkedIn' }
    };

    if (loading) {
        return (
            <div className="bg-slate-900 rounded-xl border border-slate-800 p-4">
                <div className="flex items-center gap-2 mb-3">
                    <ExternalLink className="w-4 h-4 text-violet-400" />
                    <h3 className="text-sm font-semibold text-white uppercase tracking-wider">Social Media</h3>
                </div>
                <div className="flex items-center justify-center py-4">
                    <Loader2 className="w-5 h-5 animate-spin text-slate-400" />
                </div>
            </div>
        );
    }

    if (links.length === 0) {
        return (
            <div className="bg-slate-900 rounded-xl border border-slate-800 p-4">
                <div className="flex items-center gap-2 mb-3">
                    <ExternalLink className="w-4 h-4 text-violet-400" />
                    <h3 className="text-sm font-semibold text-white uppercase tracking-wider">Social Media</h3>
                </div>
                <p className="text-slate-500 text-sm text-center py-2">No social profiles found</p>
            </div>
        );
    }

    return (
        <div className="bg-slate-900 rounded-xl border border-slate-800 p-4">
            <div className="flex items-center gap-2 mb-4">
                <ExternalLink className="w-4 h-4 text-violet-400" />
                <h3 className="text-sm font-semibold text-white uppercase tracking-wider">Social Media</h3>
            </div>
            <div className="flex flex-wrap gap-3">
                {links.map((link) => {
                    const config = platformConfig[link.platform] || { icon: '🔗', color: 'bg-slate-700', label: link.platform };
                    return (
                        <a
                            key={link.platform}
                            href={link.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className={`flex items-center gap-2 px-4 py-2 rounded-lg ${config.color} text-white hover:opacity-90 transition-opacity shadow-lg`}
                        >
                            <span className="text-lg">{config.icon}</span>
                            <span className="font-medium text-sm">{config.label}</span>
                            {link.verified && (
                                <span className="text-xs bg-white/20 px-1.5 py-0.5 rounded">✓</span>
                            )}
                        </a>
                    );
                })}
            </div>
        </div>
    );
};

export default OpponentsView;
