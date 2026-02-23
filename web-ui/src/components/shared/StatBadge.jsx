import React from 'react';

const StatBadge = ({ label, value, small }) => (
    <div className={`flex items-center gap-2 px-3 py-1.5 bg-slate-800 rounded-full border border-slate-700 ${small ? 'scale-90 origin-right' : ''}`}>
        <span className="text-xs text-slate-400">{label}</span>
        <span className="text-sm font-bold text-white">{value}</span>
    </div>
);

export default StatBadge;
