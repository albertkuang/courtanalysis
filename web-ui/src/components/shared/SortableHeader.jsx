import React from 'react';
import { ArrowUpDown } from 'lucide-react';

const SortableHeader = ({ label, sortKey, currentSort, onSort, align = 'left', className = '' }) => (
    <th
        className={`px-3 md:px-6 py-4 cursor-pointer hover:text-white transition-colors text-${align} ${className}`}
        onClick={() => onSort(sortKey)}
    >
        <div className={`flex items-center gap-1 ${align === 'center' ? 'justify-center' : ''}`}>
            {label}
            <ArrowUpDown className={`w-3 h-3 ${currentSort.key === sortKey ? 'text-tennis-blue' : 'opacity-30'}`} />
        </div>
    </th>
);

export default SortableHeader;
