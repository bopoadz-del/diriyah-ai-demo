import React, { useState } from 'react';
import { ChevronDown, ChevronRight, Link2, FileText, ExternalLink } from 'lucide-react';

/**
 * Panel showing document links with confidence bars and expandable evidence.
 * Follows existing Tailwind CSS patterns from the codebase.
 */
const LinkPanel = ({ links = [], loading = false, onLinkClick }) => {
  const [expandedLinks, setExpandedLinks] = useState({});
  const [confidenceFilter, setConfidenceFilter] = useState(0);
  const [typeFilter, setTypeFilter] = useState('all');

  const toggleExpanded = (linkId) => {
    setExpandedLinks((prev) => ({
      ...prev,
      [linkId]: !prev[linkId],
    }));
  };

  const getConfidenceColor = (confidence) => {
    if (confidence >= 0.9) return 'bg-green-500';
    if (confidence >= 0.8) return 'bg-green-400';
    if (confidence >= 0.7) return 'bg-yellow-400';
    if (confidence >= 0.6) return 'bg-orange-400';
    return 'bg-red-400';
  };

  const getEntityTypeIcon = (type) => {
    const icons = {
      BOQItem: '📋',
      SpecSection: '📄',
      ContractClause: '📝',
      DrawingRef: '📐',
      CostItem: '💰',
      PaymentCert: '💳',
      VariationOrder: '🔄',
      Invoice: '🧾',
    };
    return icons[type] || '📎';
  };

  const filteredLinks = links.filter((link) => {
    if (link.confidence < confidenceFilter) return false;
    if (typeFilter !== 'all' && link.link_type !== typeFilter) return false;
    return true;
  });

  const linkTypes = [...new Set(links.map((l) => l.link_type))];

  if (loading) {
    return (
      <div className="p-4 bg-white rounded-lg border border-gray-200">
        <div className="animate-pulse space-y-3">
          <div className="h-4 bg-gray-200 rounded w-3/4"></div>
          <div className="h-4 bg-gray-200 rounded w-1/2"></div>
          <div className="h-4 bg-gray-200 rounded w-2/3"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 bg-gray-50 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-medium text-gray-900 flex items-center gap-2">
            <Link2 className="w-4 h-4" />
            Document Links
            <span className="text-xs text-gray-500">({filteredLinks.length})</span>
          </h3>
        </div>

        {/* Filters */}
        <div className="mt-2 flex gap-2 flex-wrap">
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="text-xs border border-gray-300 rounded px-2 py-1 bg-white"
          >
            <option value="all">All Types</option>
            {linkTypes.map((type) => (
              <option key={type} value={type}>
                {type}
              </option>
            ))}
          </select>

          <div className="flex items-center gap-1 text-xs text-gray-600">
            <span>Min:</span>
            <input
              type="range"
              min="0"
              max="100"
              value={confidenceFilter * 100}
              onChange={(e) => setConfidenceFilter(e.target.value / 100)}
              className="w-20"
            />
            <span>{Math.round(confidenceFilter * 100)}%</span>
          </div>
        </div>
      </div>

      {/* Links List */}
      <div className="divide-y divide-gray-100 max-h-96 overflow-y-auto">
        {filteredLinks.length === 0 ? (
          <div className="p-4 text-center text-gray-500 text-sm">
            No links found matching filters
          </div>
        ) : (
          filteredLinks.map((link) => (
            <div key={link.id} className="p-3 hover:bg-gray-50 transition-colors">
              {/* Link Header */}
              <div
                className="flex items-start gap-2 cursor-pointer"
                onClick={() => toggleExpanded(link.id)}
              >
                <button className="mt-1 text-gray-400 hover:text-gray-600">
                  {expandedLinks[link.id] ? (
                    <ChevronDown className="w-4 h-4" />
                  ) : (
                    <ChevronRight className="w-4 h-4" />
                  )}
                </button>

                <div className="flex-1 min-w-0">
                  {/* Source -> Target */}
                  <div className="flex items-center gap-2 text-sm">
                    <span className="flex items-center gap-1">
                      <span>{getEntityTypeIcon(link.source.type)}</span>
                      <span className="font-medium text-gray-900 truncate max-w-[120px]">
                        {link.source.text}
                      </span>
                    </span>
                    <span className="text-gray-400">→</span>
                    <span className="flex items-center gap-1">
                      <span>{getEntityTypeIcon(link.target.type)}</span>
                      <span className="font-medium text-gray-900 truncate max-w-[120px]">
                        {link.target.text}
                      </span>
                    </span>
                  </div>

                  {/* Link Type & Confidence */}
                  <div className="mt-1 flex items-center gap-2">
                    <span className="text-xs text-gray-500 bg-gray-100 px-2 py-0.5 rounded">
                      {link.link_type}
                    </span>

                    {/* Confidence Bar */}
                    <div className="flex items-center gap-1 flex-1">
                      <div className="flex-1 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                        <div
                          className={`h-full ${getConfidenceColor(link.confidence)} transition-all`}
                          style={{ width: `${link.confidence * 100}%` }}
                        />
                      </div>
                      <span className="text-xs text-gray-600 font-medium">
                        {Math.round(link.confidence * 100)}%
                      </span>
                    </div>
                  </div>
                </div>

                {onLinkClick && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onLinkClick(link);
                    }}
                    className="text-gray-400 hover:text-blue-500"
                  >
                    <ExternalLink className="w-4 h-4" />
                  </button>
                )}
              </div>

              {/* Expanded Evidence */}
              {expandedLinks[link.id] && link.evidence && (
                <div className="mt-2 ml-6 p-2 bg-gray-50 rounded text-xs">
                  <div className="font-medium text-gray-700 mb-1">Evidence:</div>
                  <ul className="space-y-1">
                    {link.evidence.map((ev, idx) => (
                      <li key={idx} className="flex items-center gap-2 text-gray-600">
                        <span className="w-2 h-2 rounded-full bg-blue-400" />
                        <span className="capitalize">{ev.type.replace(/_/g, ' ')}</span>
                        <span className="text-gray-400">—</span>
                        <span>
                          {typeof ev.value === 'number'
                            ? `${Math.round(ev.value * 100)}%`
                            : ev.value}
                        </span>
                        <span className="text-gray-400 text-[10px]">
                          (weight: {Math.round(ev.weight * 100)}%)
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default LinkPanel;
