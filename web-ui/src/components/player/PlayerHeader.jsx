import React from 'react';
import { MapPin, Calendar, Trophy, Star, ExternalLink } from 'lucide-react';

const PlayerHeader = ({ player, isFavorite, onToggleFavorite }) => (
    <div className="p-6 border-b border-slate-800 bg-gradient-to-b from-slate-800 to-slate-900 pt-12 md:pt-6">
        <div className="flex justify-between items-start mb-4">
            <div className="bg-slate-800 p-2 rounded text-xs font-mono text-slate-400 border border-slate-700">ID: {player.player_id}</div>
            <div className="flex items-center gap-3">
                <button
                    onClick={onToggleFavorite}
                    className={`p-2 rounded-full border transition-colors ${isFavorite ? 'bg-amber-500/20 border-amber-500 text-amber-500' : 'bg-slate-900 border-slate-700 text-slate-500 hover:text-amber-400'}`}
                    title={isFavorite ? "Unfavorite" : "Add to Favorites"}
                >
                    <Star className={`w-5 h-5 ${isFavorite ? 'fill-amber-500' : ''}`} />
                </button>
                <a href={`https://app.utrsports.net/profiles/${player.player_id}`} target="_blank" rel="noreferrer" className="text-tennis-blue hover:text-white mr-8 md:mr-0">
                    <ExternalLink className="w-4 h-4" />
                </a>
            </div>
        </div>
        <h2 className="text-2xl font-bold text-white mb-1">{player.name}</h2>
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-slate-400 mb-6">
            <div className="flex items-center gap-2">
                <MapPin className="w-3 h-3" /> {player.location || player.country || 'Unknown'}
            </div>
            {(player.age || player.birth_date) && (
                <div className="flex items-center gap-2 border-l border-slate-700 pl-4">
                    <Calendar className="w-3 h-3" /> {player.age ? `${player.age} yrs` : ''}
                    {player.birth_date && <span className="text-[10px] text-slate-500">({player.birth_date.split('T')[0]})</span>}
                </div>
            )}
            {player.pro_rank && (
                <div className="flex items-center gap-2 border-l border-slate-700 pl-4 text-amber-400 font-semibold">
                    <Trophy className="w-3 h-3" /> {player.pro_rank}
                </div>
            )}
        </div>

        <div className="grid grid-cols-2 gap-3 mb-4">
            <div className="bg-slate-950 p-4 rounded-xl border border-slate-800">
                <div className="text-slate-500 text-xs uppercase font-semibold mb-1">Singles UTR</div>
                <div className="text-3xl font-bold text-tennis-green">{player.utr_singles?.toFixed(2)}</div>
            </div>
            <div className="bg-slate-950 p-4 rounded-xl border border-slate-800">
                <div className="text-slate-500 text-xs uppercase font-semibold mb-1">Doubles UTR</div>
                <div className="text-xl font-bold text-slate-300">{player.utr_doubles?.toFixed(2) || '-'}</div>
            </div>
        </div>

        {/* Advanced Metrics Grid */}
        <div className="grid grid-cols-3 gap-2">
            <div className="bg-slate-950/50 p-2 rounded-lg border border-slate-800 text-center">
                <div className="text-[10px] text-slate-500 uppercase">Comebacks</div>
                <div className="text-lg font-bold text-emerald-400">{player.comeback_wins || 0}</div>
            </div>
            <div className="bg-slate-950/50 p-2 rounded-lg border border-slate-800 text-center">
                <div className="text-[10px] text-slate-500 uppercase">Tiebreaks</div>
                <div className="text-lg font-bold text-slate-200">
                    <span className="text-tennis-green">{player.tiebreak_wins || 0}</span>
                    <span className="text-slate-600 mx-1">/</span>
                    <span className="text-rose-400">{player.tiebreak_losses || 0}</span>
                </div>
            </div>
            <div className="bg-slate-950/50 p-2 rounded-lg border border-slate-800 text-center">
                <div className="text-[10px] text-slate-500 uppercase">3-Sets</div>
                <div className="text-lg font-bold text-slate-200">
                    <span className="text-tennis-green">{player.three_set_wins || 0}</span>
                    <span className="text-slate-600 mx-1">/</span>
                    <span className="text-rose-400">{player.three_set_losses || 0}</span>
                </div>
            </div>
        </div>
    </div>
);

export default PlayerHeader;
