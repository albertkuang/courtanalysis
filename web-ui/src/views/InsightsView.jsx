import React, { useMemo } from 'react';
import { TrendingUp, Activity, TrendingDown, Lightbulb } from 'lucide-react';
import { SelectFilter, StatBadge } from '../components/shared';

const CardRow = ({ title, icon, data, type, onPlayerClick }) => (
    <div className="mb-8 p-4">
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
                            <div className="flex flex-col items-center">
                                <span className={`flex items-center gap-1 text-xl font-bold ${p.year_delta > 0 ? 'text-emerald-400' : p.year_delta < 0 ? 'text-rose-400' : 'text-slate-400'}`}>
                                    {p.year_delta > 0 ? <TrendingUp className="w-4 h-4" /> : p.year_delta < 0 ? <TrendingDown className="w-4 h-4" /> : null}
                                    {p.year_delta > 0 ? '+' : ''}{p.year_delta?.toFixed(2)}
                                </span>
                                <span className="text-[10px] uppercase text-slate-500">1YR Change</span>
                            </div>
                        )}
                        {type === 'clutch' && (
                            <div className="flex justify-around">
                                <div>
                                    <div className="text-sm font-bold text-white">
                                        {Math.round((p.tiebreak_wins / ((p.tiebreak_wins + p.tiebreak_losses) || 1)) * 100)}%
                                    </div>
                                    <div className="text-[8px] text-slate-500">TB</div>
                                </div>
                                <div>
                                    <div className="text-sm font-bold text-white">
                                        {Math.round((p.three_set_wins / ((p.three_set_wins + p.three_set_losses) || 1)) * 100)}%
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

const InsightsView = ({
    players,
    minUtr,
    setMinUtr,
    country,
    setCountry,
    gender,
    setGender,
    category,
    setCategory,
    onPlayerClick
}) => {
    // Filter by Min UTR and other filters
    const filtered = useMemo(() => {
        if (!players) return [];
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

    return (
        <div className="flex flex-col h-full overflow-hidden">
            {/* FILTERS BAR */}
            <div className="p-4 border-b border-slate-800 bg-slate-900/50 backdrop-blur flex flex-col md:flex-row gap-3 md:items-center justify-between overflow-x-auto shrink-0">
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
                <StatBadge label="Analyzed" value={players?.length || 0} />
            </div>

            <div className="flex-1 overflow-auto space-y-4 pb-24 md:pb-6">
                <CardRow
                    title="Comeback Kings (Most wins after losing 1st set)"
                    icon={<TrendingUp className="text-emerald-400" />}
                    data={comebackKings}
                    type="comeback"
                    onPlayerClick={onPlayerClick}
                />

                <CardRow
                    title="Fastest Risers (Top 1Y Growth)"
                    icon={<Activity className="text-tennis-blue" />}
                    data={risers}
                    type="delta"
                    onPlayerClick={onPlayerClick}
                />

                <CardRow
                    title="Biggest Fallers (Top 1Y Drop)"
                    icon={<TrendingDown className="text-rose-400" />}
                    data={fallers}
                    type="delta"
                    onPlayerClick={onPlayerClick}
                />

                <CardRow
                    title="Clutch Performers (>60% TB & 3-Set Win Rate)"
                    icon={<Lightbulb className="text-yellow-400" />}
                    data={clutchPlayers}
                    type="clutch"
                    onPlayerClick={onPlayerClick}
                />
            </div>
        </div>
    );
};

export default InsightsView;
