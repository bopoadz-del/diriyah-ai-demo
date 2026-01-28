import React, { useEffect, useRef, useState, useCallback } from 'react';
import { ZoomIn, ZoomOut, Maximize2, RefreshCw } from 'lucide-react';

/**
 * Knowledge graph visualization component.
 * Uses SVG for rendering nodes and edges.
 * Can be enhanced with D3.js or react-flow for more complex visualizations.
 */
const LinkGraph = ({ nodes = [], edges = [], onNodeClick, stats = {} }) => {
  const svgRef = useRef(null);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [dragging, setDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [selectedNode, setSelectedNode] = useState(null);
  const [nodePositions, setNodePositions] = useState({});

  // Colors for different entity types
  const typeColors = {
    BOQItem: '#3B82F6',       // blue
    SpecSection: '#10B981',   // green
    ContractClause: '#F59E0B', // amber
    DrawingRef: '#8B5CF6',    // purple
    CostItem: '#EC4899',      // pink
    PaymentCert: '#14B8A6',   // teal
    VariationOrder: '#F97316', // orange
    Invoice: '#6366F1',       // indigo
  };

  // Calculate node positions using a simple force-directed layout simulation
  const calculatePositions = useCallback(() => {
    if (nodes.length === 0) return;

    const width = 600;
    const height = 400;
    const positions = {};

    // Initialize positions in a circle
    nodes.forEach((node, i) => {
      const angle = (2 * Math.PI * i) / nodes.length;
      const radius = Math.min(width, height) * 0.35;
      positions[node.id] = {
        x: width / 2 + radius * Math.cos(angle),
        y: height / 2 + radius * Math.sin(angle),
      };
    });

    // Simple force simulation (a few iterations)
    for (let iter = 0; iter < 50; iter++) {
      // Repulsion between nodes
      nodes.forEach((node1) => {
        nodes.forEach((node2) => {
          if (node1.id === node2.id) return;
          const dx = positions[node1.id].x - positions[node2.id].x;
          const dy = positions[node1.id].y - positions[node2.id].y;
          const dist = Math.sqrt(dx * dx + dy * dy) || 1;
          const force = 1000 / (dist * dist);
          positions[node1.id].x += (dx / dist) * force;
          positions[node1.id].y += (dy / dist) * force;
        });
      });

      // Attraction along edges
      edges.forEach((edge) => {
        const source = positions[edge.source];
        const target = positions[edge.target];
        if (!source || !target) return;
        const dx = target.x - source.x;
        const dy = target.y - source.y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const force = dist * 0.01;
        source.x += (dx / dist) * force;
        source.y += (dy / dist) * force;
        target.x -= (dx / dist) * force;
        target.y -= (dy / dist) * force;
      });

      // Keep nodes within bounds
      nodes.forEach((node) => {
        positions[node.id].x = Math.max(50, Math.min(width - 50, positions[node.id].x));
        positions[node.id].y = Math.max(50, Math.min(height - 50, positions[node.id].y));
      });
    }

    setNodePositions(positions);
  }, [nodes, edges]);

  useEffect(() => {
    calculatePositions();
  }, [calculatePositions]);

  const handleMouseDown = (e) => {
    if (e.target === svgRef.current) {
      setDragging(true);
      setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
    }
  };

  const handleMouseMove = (e) => {
    if (dragging) {
      setPan({
        x: e.clientX - dragStart.x,
        y: e.clientY - dragStart.y,
      });
    }
  };

  const handleMouseUp = () => {
    setDragging(false);
  };

  const handleNodeClick = (node) => {
    setSelectedNode(node.id === selectedNode ? null : node.id);
    if (onNodeClick) {
      onNodeClick(node);
    }
  };

  const getConfidenceOpacity = (confidence) => {
    return 0.3 + confidence * 0.7;
  };

  if (nodes.length === 0) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-8 text-center">
        <div className="text-gray-400 text-lg mb-2">No graph data</div>
        <p className="text-gray-500 text-sm">
          Process documents to build the knowledge graph
        </p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
      {/* Toolbar */}
      <div className="px-4 py-2 bg-gray-50 border-b border-gray-200 flex items-center justify-between">
        <div className="text-sm font-medium text-gray-700">
          Knowledge Graph
          <span className="ml-2 text-gray-500 text-xs">
            {nodes.length} nodes, {edges.length} edges
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setZoom((z) => Math.min(2, z + 0.1))}
            className="p-1 hover:bg-gray-200 rounded"
            title="Zoom in"
          >
            <ZoomIn className="w-4 h-4 text-gray-600" />
          </button>
          <button
            onClick={() => setZoom((z) => Math.max(0.5, z - 0.1))}
            className="p-1 hover:bg-gray-200 rounded"
            title="Zoom out"
          >
            <ZoomOut className="w-4 h-4 text-gray-600" />
          </button>
          <button
            onClick={() => {
              setZoom(1);
              setPan({ x: 0, y: 0 });
            }}
            className="p-1 hover:bg-gray-200 rounded"
            title="Reset view"
          >
            <Maximize2 className="w-4 h-4 text-gray-600" />
          </button>
          <button
            onClick={calculatePositions}
            className="p-1 hover:bg-gray-200 rounded"
            title="Recalculate layout"
          >
            <RefreshCw className="w-4 h-4 text-gray-600" />
          </button>
        </div>
      </div>

      {/* SVG Graph */}
      <svg
        ref={svgRef}
        width="100%"
        height="400"
        className="cursor-move"
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      >
        <g transform={`translate(${pan.x}, ${pan.y}) scale(${zoom})`}>
          {/* Edges */}
          {edges.map((edge) => {
            const source = nodePositions[edge.source];
            const target = nodePositions[edge.target];
            if (!source || !target) return null;

            return (
              <g key={edge.id}>
                <line
                  x1={source.x}
                  y1={source.y}
                  x2={target.x}
                  y2={target.y}
                  stroke="#9CA3AF"
                  strokeWidth={2}
                  strokeOpacity={getConfidenceOpacity(edge.confidence)}
                />
                {/* Arrow marker */}
                <circle
                  cx={(source.x + target.x * 2) / 3}
                  cy={(source.y + target.y * 2) / 3}
                  r={3}
                  fill="#9CA3AF"
                  fillOpacity={getConfidenceOpacity(edge.confidence)}
                />
              </g>
            );
          })}

          {/* Nodes */}
          {nodes.map((node) => {
            const pos = nodePositions[node.id];
            if (!pos) return null;

            const isSelected = selectedNode === node.id;
            const color = typeColors[node.type] || '#6B7280';

            return (
              <g
                key={node.id}
                transform={`translate(${pos.x}, ${pos.y})`}
                onClick={() => handleNodeClick(node)}
                className="cursor-pointer"
              >
                <circle
                  r={isSelected ? 22 : 18}
                  fill={color}
                  stroke={isSelected ? '#1F2937' : 'white'}
                  strokeWidth={isSelected ? 3 : 2}
                  className="transition-all duration-200"
                />
                <text
                  textAnchor="middle"
                  dy="4"
                  fill="white"
                  fontSize="10"
                  fontWeight="bold"
                >
                  {node.type.slice(0, 3).toUpperCase()}
                </text>
                {/* Label */}
                <text
                  textAnchor="middle"
                  dy="32"
                  fill="#374151"
                  fontSize="9"
                  className="pointer-events-none"
                >
                  {node.label.slice(0, 15)}
                  {node.label.length > 15 ? '...' : ''}
                </text>
              </g>
            );
          })}
        </g>
      </svg>

      {/* Legend */}
      <div className="px-4 py-2 bg-gray-50 border-t border-gray-200">
        <div className="flex flex-wrap gap-3 text-xs">
          {Object.entries(typeColors).map(([type, color]) => {
            const count = nodes.filter((n) => n.type === type).length;
            if (count === 0) return null;
            return (
              <div key={type} className="flex items-center gap-1">
                <div
                  className="w-3 h-3 rounded-full"
                  style={{ backgroundColor: color }}
                />
                <span className="text-gray-600">
                  {type} ({count})
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default LinkGraph;
