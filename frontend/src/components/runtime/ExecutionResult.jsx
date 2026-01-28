import React from 'react';

/**
 * Display execution results with status indicators.
 */
export default function ExecutionResult({ result }) {
  if (!result) {
    return null;
  }

  const isSuccess = result.status === 'success';
  const isDryRun = result.status === 'dry_run';
  const isError = result.status === 'error';

  return (
    <div className="rounded-lg border overflow-hidden">
      {/* Status Header */}
      <div
        className={`flex items-center gap-2 px-4 py-3 ${
          isSuccess
            ? 'bg-green-900/50 border-b border-green-700'
            : isDryRun
            ? 'bg-blue-900/50 border-b border-blue-700'
            : 'bg-red-900/50 border-b border-red-700'
        }`}
      >
        {isSuccess && (
          <svg className="w-5 h-5 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        )}
        {isDryRun && (
          <svg className="w-5 h-5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        )}
        {isError && (
          <svg className="w-5 h-5 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        )}
        <span
          className={`font-medium ${
            isSuccess ? 'text-green-300' : isDryRun ? 'text-blue-300' : 'text-red-300'
          }`}
        >
          {isSuccess ? 'Execution Successful' : isDryRun ? 'Dry Run Complete' : 'Execution Failed'}
        </span>

        {/* Timing info */}
        {result.execution_time && (
          <span className="ml-auto text-sm text-gray-400">
            {(result.execution_time * 1000).toFixed(1)}ms
          </span>
        )}
        {result.memory_used && (
          <span className="text-sm text-gray-400">
            {(result.memory_used / 1024).toFixed(1)}KB
          </span>
        )}
      </div>

      {/* Output */}
      <div className="p-4 bg-gray-900">
        {result.error_message && (
          <div className="mb-4 p-3 bg-red-900/30 rounded text-red-300 text-sm font-mono">
            {result.error_message}
          </div>
        )}

        {result.output !== null && result.output !== undefined && (
          <div>
            <h4 className="text-sm font-medium text-gray-400 mb-2">Output:</h4>
            <pre className="bg-gray-800 p-3 rounded text-sm text-gray-200 overflow-auto max-h-60 font-mono">
              {typeof result.output === 'object'
                ? JSON.stringify(result.output, null, 2)
                : String(result.output)}
            </pre>
          </div>
        )}

        {/* Logs */}
        {result.logs && result.logs.length > 0 && (
          <div className="mt-4">
            <h4 className="text-sm font-medium text-gray-400 mb-2">Logs:</h4>
            <div className="space-y-1">
              {result.logs.map((log, index) => (
                <div
                  key={index}
                  className={`text-xs font-mono p-2 rounded ${
                    log.level === 'ERROR'
                      ? 'bg-red-900/30 text-red-300'
                      : log.level === 'WARNING'
                      ? 'bg-yellow-900/30 text-yellow-300'
                      : 'bg-gray-800 text-gray-300'
                  }`}
                >
                  <span className="font-bold">[{log.level}]</span> {log.message}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
