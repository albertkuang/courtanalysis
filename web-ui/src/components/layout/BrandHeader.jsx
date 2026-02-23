import React from 'react';
import { Trophy, LogOut, User as UserIcon } from 'lucide-react';

const BrandHeader = ({ small, user, onLoginClick, onLogout }) => (
    <div className={`flex flex-col ${small ? 'flex-row items-center gap-3' : 'mb-8 px-2 gap-4'}`}>
        <div className={`flex items-center gap-3`}>
            <div className="bg-tennis-green p-1.5 md:p-2 rounded-lg">
                <Trophy className="text-slate-900 w-5 h-5 md:w-6 md:h-6" />
            </div>
            <h1 className="text-lg md:text-xl font-bold text-white tracking-tight">
                CourtSide <span className={`text-tennis-blue ${small ? 'inline font-normal ml-1' : 'block text-xs font-medium'}`}>ANALYTICS</span>
            </h1>
        </div>

        {!small && (
            <div className="w-full">
                {user ? (
                    <div className="bg-slate-800 p-3 rounded-xl border border-slate-700 flex items-center justify-between group">
                        <div className="flex items-center gap-2 overflow-hidden">
                            <div className="w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center text-slate-300 font-bold">
                                {user.name?.[0]?.toUpperCase() || <UserIcon size={16} />}
                            </div>
                            <div className="truncate">
                                <div className="text-sm font-medium text-white truncate max-w-[100px]">{user.name || 'User'}</div>
                                <div className="text-[10px] text-slate-400">Pro Plan</div>
                            </div>
                        </div>
                        <button onClick={onLogout} className="text-slate-500 hover:text-rose-400 transition-colors p-1">
                            <LogOut size={16} />
                        </button>
                    </div>
                ) : (
                    <button
                        onClick={onLoginClick}
                        className="w-full bg-slate-800 hover:bg-slate-700 border border-slate-700 text-white py-2 rounded-lg text-sm font-medium transition-colors flex items-center justify-center gap-2"
                    >
                        <UserIcon size={16} /> Login / Sign Up
                    </button>
                )}
            </div>
        )}
    </div>
);

export default BrandHeader;
