import React, { useMemo } from 'react';
import { Trophy, Activity } from 'lucide-react';
import {
    PieChart, Pie, Cell, Tooltip, ResponsiveContainer,
    RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis
} from 'recharts';

const WinLossDonut = ({ matches, playerId }) => {
    const data = useMemo(() => {
        if (!matches) return [];
        const wins = matches.filter(m => String(m.winner_id) === String(playerId)).length;
        const losses = matches.length - wins;
        return [
            { name: 'Wins', value: wins, color: '#10b981' },
            { name: 'Losses', value: losses, color: '#fb7185' }
        ];
    }, [matches, playerId]);

    const winRate = useMemo(() => {
        if (!matches || matches.length === 0) return 0;
        return Math.round((data[0].value / matches.length) * 100);
    }, [data, matches]);

    if (!matches || matches.length === 0) return null;

    return (
        <div className="flex flex-col items-center">
            <h3 className="text-sm font-semibold text-white uppercase tracking-wider mb-2 w-full text-left flex items-center gap-2">
                <Trophy className="w-4 h-4 text-emerald-400" /> Win Rate
            </h3>
            <div className="h-40 w-full bg-slate-950 rounded-lg border border-slate-800 relative flex justify-center items-center">
                <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                        <Pie data={data} cx="50%" cy="50%" innerRadius={35} outerRadius={50} paddingAngle={5} dataKey="value" stroke="none">
                            {data.map((entry, index) => (
                                <Cell key={`cell-${index}`} fill={entry.color} />
                            ))}
                        </Pie>
                        <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', fontSize: '12px' }} itemStyle={{ color: '#fff' }} />
                    </PieChart>
                </ResponsiveContainer>
                <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                    <div className="text-center">
                        <div className="text-xl font-bold text-white">{winRate}%</div>
                        <div className="text-[9px] text-slate-500 uppercase">Win Pct</div>
                    </div>
                </div>
            </div>
        </div>
    );
};

const ClutchRadar = ({ player, matches }) => {
    const data = useMemo(() => {
        if (!player) return [];
        const tbTotal = (player.tiebreak_wins || 0) + (player.tiebreak_losses || 0);
        const tbRate = tbTotal > 0 ? Math.round((player.tiebreak_wins / tbTotal) * 100) : 50;
        const threeTotal = (player.three_set_wins || 0) + (player.three_set_losses || 0);
        const threeRate = threeTotal > 0 ? Math.round((player.three_set_wins / threeTotal) * 100) : 50;
        let formRate = 50;
        if (matches && matches.length > 0) {
            const recent = matches.slice(0, 10);
            const wins = recent.filter(m => String(m.winner_id) === String(player.player_id)).length;
            formRate = Math.round((wins / recent.length) * 100);
        }
        const grit = Math.min((player.comeback_wins || 0) * 20, 100);
        return [
            { subject: 'Tiebreaks', A: tbRate, fullMark: 100 },
            { subject: '3-Sets', A: threeRate, fullMark: 100 },
            { subject: 'Form', A: formRate, fullMark: 100 },
            { subject: 'Grit', A: grit, fullMark: 100 },
        ];
    }, [player, matches]);

    return (
        <div className="flex flex-col items-center">
            <h3 className="text-sm font-semibold text-white uppercase tracking-wider mb-2 w-full text-left flex items-center gap-2">
                <Activity className="w-4 h-4 text-violet-400" /> Attributes
            </h3>
            <div className="h-40 w-full bg-slate-950 rounded-lg border border-slate-800 flex justify-center items-center">
                <ResponsiveContainer width="100%" height="100%">
                    <RadarChart cx="50%" cy="50%" outerRadius="65%" data={data}>
                        <PolarGrid stroke="#334155" />
                        <PolarAngleAxis dataKey="subject" tick={{ fill: '#94a3b8', fontSize: 10 }} />
                        <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
                        <Radar name="Player" dataKey="A" stroke="#8b5cf6" strokeWidth={2} fill="#8b5cf6" fillOpacity={0.3} />
                        <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', fontSize: '12px' }} itemLine={false} />
                    </RadarChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
};

export { WinLossDonut, ClutchRadar };
