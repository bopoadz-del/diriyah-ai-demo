import React, { useState } from 'react';
import { Link2 } from 'lucide-react';

/**
 * Small badge showing link count with tooltip preview.
 * For displaying on documents in lists or cards.
 */
const LinkBadge = ({ linkCount = 0, topLinks = [], onClick }) => {
  const [showTooltip, setShowTooltip] = useState(false);

  if (linkCount === 0) {
    return null;
  }

  const getBadgeColor = () => {
    if (linkCount >= 10) return 'bg-green-100 text-green-800 border-green-200';
    if (linkCount >= 5) return 'bg-blue-100 text-blue-800 border-blue-200';
    return 'bg-gray-100 text-gray-800 border-gray-200';
  };

  const getConfidenceBadge = (confidence) => {
    if (confidence >= 0.9) return 'bg-green-500';
    if (confidence >= 0.8) return 'bg-green-400';
    if (confidence >= 0.7) return 'bg-yellow-400';
    return 'bg-orange-400';
  };

  return (
    <div className="relative inline-block">
      <button
        onClick={onClick}
        onMouseEnter={() => setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
        className={`
          inline-flex items-center gap-1 px-2 py-0.5 rounded-full
          text-xs font-medium border
          hover:opacity-80 transition-opacity
          ${getBadgeColor()}
        `}
      >
        <Link2 className="w-3 h-3" />
        <span>{linkCount}</span>
      </button>

      {/* Tooltip */}
      {showTooltip && topLinks.length > 0 && (
        <div className="absolute z-50 bottom-full left-1/2 -translate-x-1/2 mb-2 w-64">
          <div className="bg-gray-900 text-white text-xs rounded-lg shadow-lg p-3">
            <div className="font-medium mb-2">Top Links</div>
            <div className="space-y-2">
              {topLinks.slice(0, 3).map((link, idx) => (
                <div key={idx} className="flex items-start gap-2">
                  <div
                    className={`w-2 h-2 rounded-full mt-1 ${getConfidenceBadge(
                      link.confidence
                    )}`}
                  />
                  <div className="flex-1 min-w-0">
                    <div className="truncate text-gray-300">
                      {link.source?.text?.slice(0, 30) || 'Source'}
                    </div>
                    <div className="text-gray-500 text-[10px]">
                      → {link.target?.text?.slice(0, 30) || 'Target'}
                    </div>
                    <div className="text-gray-400 text-[10px]">
                      {link.link_type} ({Math.round(link.confidence * 100)}%)
                    </div>
                  </div>
                </div>
              ))}
            </div>
            {linkCount > 3 && (
              <div className="mt-2 text-gray-400 text-[10px]">
                +{linkCount - 3} more links
              </div>
            )}
            {/* Arrow */}
            <div className="absolute left-1/2 -translate-x-1/2 -bottom-1 w-2 h-2 bg-gray-900 rotate-45" />
          </div>
        </div>
      )}
    </div>
  );
};

export default LinkBadge;
