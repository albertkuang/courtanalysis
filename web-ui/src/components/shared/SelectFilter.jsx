import React from 'react';

const SelectFilter = ({ value, onChange, options, width = 'w-auto' }) => (
  <select
    value={value}
    onChange={(e) => onChange(e.target.value)}
    className={`bg-slate-800 border border-slate-700 rounded-lg px-2 py-2 text-xs md:text-sm focus:outline-none text-white ${width}`}
  >
    {options.map(o => <option key={o.val} value={o.val}>{o.txt}</option>)}
  </select>
);

export default SelectFilter;
