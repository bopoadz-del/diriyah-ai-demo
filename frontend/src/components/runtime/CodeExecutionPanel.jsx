import React, { useState } from 'react';
import CodeEditor from './CodeEditor';
import ExecutionResult from './ExecutionResult';
import ExecutionHistory from './ExecutionHistory';
import FunctionLibrary from './FunctionLibrary';
import { useCodeExecution } from '../../hooks/useCodeExecution';

/**
 * Main panel for code generation and execution.
 */
export default function CodeExecutionPanel({ projectId }) {
  const [query, setQuery] = useState('');
  const [showCode, setShowCode] = useState(false);
  const [showFunctions, setShowFunctions] = useState(false);
  const [activeTab, setActiveTab] = useState('execute'); // execute | history | functions

  const { execute, loading, result, error, generatedCode } = useCodeExecution();

  const handleExecute = async (dryRun = false) => {
    if (!query.trim()) return;
    await execute(query, { project_id: projectId }, dryRun);
    setShowCode(true);
  };

  const handleHistorySelect = async (item) => {
    // Fetch full execution details
    try {
      const response = await fetch(`/api/runtime/execution/${item.id}`);
      if (response.ok) {
        const data = await response.json();
        // Update state with historical result
        setQuery(item.query);
        setShowCode(true);
      }
    } catch (err) {
      console.error('Failed to load execution:', err);
    }
  };

  const exampleQueries = [
    "What's the cost variance if steel prices increase 15%?",
    "Calculate total quantities for all concrete items",
    "Run Monte Carlo simulation on BOQ costs",
    "What's the schedule slip forecast?",
  ];

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      {/* Header */}
      <div className="border-b border-gray-800 p-4">
        <h1 className="text-xl font-bold">Analytics Runtime</h1>
        <p className="text-sm text-gray-400 mt-1">
          Generate and execute Python code from natural language queries
        </p>
      </div>

      <div className="flex">
        {/* Main Panel */}
        <div className="flex-1 p-6">
          {/* Tabs */}
          <div className="flex gap-4 mb-6 border-b border-gray-800">
            <button
              onClick={() => setActiveTab('execute')}
              className={`pb-3 px-1 text-sm font-medium transition-colors ${
                activeTab === 'execute'
                  ? 'text-blue-400 border-b-2 border-blue-400'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              Execute Query
            </button>
            <button
              onClick={() => setActiveTab('history')}
              className={`pb-3 px-1 text-sm font-medium transition-colors ${
                activeTab === 'history'
                  ? 'text-blue-400 border-b-2 border-blue-400'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              History
            </button>
            <button
              onClick={() => setActiveTab('functions')}
              className={`pb-3 px-1 text-sm font-medium transition-colors ${
                activeTab === 'functions'
                  ? 'text-blue-400 border-b-2 border-blue-400'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              Function Library
            </button>
          </div>

          {activeTab === 'execute' && (
            <div className="space-y-6">
              {/* Query Input */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  What would you like to analyze?
                </label>
                <textarea
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="e.g., What's the cost variance if steel prices increase 15%?"
                  className="w-full h-24 bg-gray-800 border border-gray-700 rounded-lg p-3 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 resize-none"
                />

                {/* Example Queries */}
                <div className="flex flex-wrap gap-2 mt-2">
                  {exampleQueries.map((example, index) => (
                    <button
                      key={index}
                      onClick={() => setQuery(example)}
                      className="text-xs px-2 py-1 bg-gray-800 hover:bg-gray-700 text-gray-400 hover:text-white rounded transition-colors"
                    >
                      {example}
                    </button>
                  ))}
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex gap-3">
                <button
                  onClick={() => handleExecute(false)}
                  disabled={loading || !query.trim()}
                  className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 disabled:cursor-not-allowed rounded-lg font-medium transition-colors"
                >
                  {loading ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                      Executing...
                    </>
                  ) : (
                    <>
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      Execute
                    </>
                  )}
                </button>

                <button
                  onClick={() => handleExecute(true)}
                  disabled={loading || !query.trim()}
                  className="flex items-center gap-2 px-4 py-2 bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 disabled:cursor-not-allowed rounded-lg font-medium transition-colors"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
                  </svg>
                  Generate Only
                </button>

                <button
                  onClick={() => setShowCode(!showCode)}
                  className="flex items-center gap-2 px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg font-medium transition-colors ml-auto"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
                  </svg>
                  {showCode ? 'Hide Code' : 'Show Code'}
                </button>
              </div>

              {/* Error Display */}
              {error && (
                <div className="p-4 bg-red-900/30 border border-red-700 rounded-lg text-red-300">
                  {error}
                </div>
              )}

              {/* Generated Code */}
              {showCode && generatedCode && (
                <div>
                  <h3 className="text-sm font-medium text-gray-400 mb-2">Generated Code:</h3>
                  <CodeEditor code={generatedCode} readOnly />
                </div>
              )}

              {/* Execution Result */}
              {result && (
                <div>
                  <h3 className="text-sm font-medium text-gray-400 mb-2">Result:</h3>
                  <ExecutionResult result={result} />
                </div>
              )}
            </div>
          )}

          {activeTab === 'history' && (
            <ExecutionHistory projectId={projectId} onSelect={handleHistorySelect} />
          )}

          {activeTab === 'functions' && (
            <FunctionLibrary
              onSelectFunction={(func) => {
                setQuery(`Use ${func.name} to analyze the project data`);
                setActiveTab('execute');
              }}
            />
          )}
        </div>

        {/* Side Panel - Quick Stats */}
        <div className="w-80 border-l border-gray-800 p-4 hidden lg:block">
          <h3 className="text-sm font-medium text-gray-400 mb-4">Quick Tips</h3>

          <div className="space-y-4">
            <div className="p-3 bg-gray-800 rounded-lg">
              <h4 className="text-sm font-medium text-white mb-1">Cost Analysis</h4>
              <p className="text-xs text-gray-400">
                Ask about cost variances, budget impacts, or "what-if" scenarios.
              </p>
            </div>

            <div className="p-3 bg-gray-800 rounded-lg">
              <h4 className="text-sm font-medium text-white mb-1">Schedule Forecasting</h4>
              <p className="text-xs text-gray-400">
                Query about delays, SPI, or schedule slip forecasts.
              </p>
            </div>

            <div className="p-3 bg-gray-800 rounded-lg">
              <h4 className="text-sm font-medium text-white mb-1">Simulations</h4>
              <p className="text-xs text-gray-400">
                Run Monte Carlo simulations for risk analysis.
              </p>
            </div>

            <div className="p-3 bg-gray-800 rounded-lg">
              <h4 className="text-sm font-medium text-white mb-1">BOQ Analysis</h4>
              <p className="text-xs text-gray-400">
                Calculate totals, quantities, or material breakdowns.
              </p>
            </div>
          </div>

          {/* Project Context */}
          {projectId && (
            <div className="mt-6 p-3 bg-blue-900/30 border border-blue-800 rounded-lg">
              <h4 className="text-sm font-medium text-blue-300 mb-1">Project Context</h4>
              <p className="text-xs text-blue-200">
                Queries will use data from project #{projectId}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
