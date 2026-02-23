import React from 'react';
import {
    Trophy, Users, Star, Calendar, Activity, Lightbulb,
    MapPin, TrendingUp, GraduationCap, Target, FileText,
    Search, BarChart3, Newspaper, ChevronRight
} from 'lucide-react';

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

const NavMenu = ({ view, setView, category, setCategory, setCountry, setMinUtr, gender }) => (
    <nav className="flex-1 space-y-2 overflow-y-auto py-4">
        <NavItem icon={<Calendar />} label="Recent Matches" active={view === 'recent'} onClick={() => setView('recent')} />
        <NavItem icon={<Users />} label="Junior Scout" active={view === 'scout' && category === 'junior'} onClick={() => { setView('scout'); if (setCategory) setCategory('junior'); }} />
        <NavItem icon={<GraduationCap />} label="College Players" active={view === 'scout' && category === 'college'} onClick={() => { setView('scout'); if (setCategory) { setCategory('college'); setCountry('ALL'); } }} />
        <NavItem icon={<Target />} label="Pro Scout" active={view === 'scout' && category === 'adult'} onClick={() => { setView('scout'); if (setCategory) { setCategory('adult'); setCountry('ALL'); setMinUtr(gender === 'M' ? 12 : 10); } }} />
        <NavItem icon={<Star />} label="Favorites" active={view === 'favorites'} onClick={() => setView('favorites')} />
        <NavItem icon={<Newspaper />} label="News Pulse" active={view === 'news'} onClick={() => setView('news')} />
        <NavItem icon={<Lightbulb />} label="Insights" active={view === 'insights'} onClick={() => setView('insights')} />
        <NavItem icon={<BarChart3 />} label="Stats Explorer" active={view === 'stats'} onClick={() => setView('stats')} />
        <NavItem icon={<TrendingUp />} label="Elo Rankings" active={view === 'tennis_elo'} onClick={() => setView('tennis_elo')} />
        <NavItem icon={<Trophy />} label="Grand Slam PBP" active={view === 'slam_pbp'} onClick={() => setView('slam_pbp')} />
        <NavItem icon={<Activity />} label="Compare" active={view === 'compare'} onClick={() => setView('compare')} />
        <NavItem icon={<MapPin />} label="Tournaments" active={view === 'tournaments'} onClick={() => setView('tournaments')} />
        <NavItem icon={<Trophy />} label="Tournament History" active={view === 'tournamenthistory'} onClick={() => setView('tournamenthistory')} />
        <NavItem icon={<GraduationCap />} label="ITF Junior Analysis" active={view === 'junioranalysis'} onClick={() => setView('junioranalysis')} />
        <NavItem icon={<Search />} label="College Scout" active={view === 'college_scout'} onClick={() => setView('college_scout')} />
        <NavItem icon={<Target />} label="Match Intelligence" active={view === 'advanced_analysis'} onClick={() => setView('advanced_analysis')} />
        <NavItem icon={<FileText />} label="Report Generator" active={view === 'report'} onClick={() => setView('report')} />
    </nav>
);

export { NavMenu, NavItem, MobileNavItem };
