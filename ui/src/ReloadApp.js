import React, { useState, useEffect } from 'react';
import './index.css';

const API_URL = process.env.REACT_APP_API_URL || '/api';

const Toast = ({ message, visible }) => {
  if (!visible) return null;
  return (
    <div className="fixed bottom-4 right-4 bg-black text-white px-3 py-2 rounded font-mono text-sm z-50">
      {message}
    </div>
  );
};

const StatusCard = ({ title, value, description, color = "gray" }) => (
  <div className={`p-4 border border-${color}-300 bg-${color}-50 rounded`}>
    <div className={`text-2xl font-bold text-${color}-800 mb-1`}>{value}</div>
    <div className={`text-sm font-semibold text-${color}-700 mb-1`}>{title}</div>
    <div className={`text-xs text-${color}-600`}>{description}</div>
  </div>
);

const ReloadApp = () => {
  const [toast, setToast] = useState({ message: '', visible: false });
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState(null);
  const [csvPath, setCsvPath] = useState('');
  const [jsonFolder, setJsonFolder] = useState('');

  useEffect(() => {
    loadStatus();
  }, []);

  const loadStatus = async () => {
    try {
      const response = await fetch(`${API_URL}/expert/status`);
      const data = await response.json();
      setStatus(data);
    } catch (error) {
      console.error('Failed to load status:', error);
    }
  };

  const handleReindex = async () => {
    if (!csvPath && !jsonFolder) {
      setToast({ message: '[error: specify at least one path]', visible: true });
      setTimeout(() => setToast({ message: '', visible: false }), 2000);
      return;
    }

    setLoading(true);

    try {
      const requestBody = {};
      if (csvPath) requestBody.csv_path = csvPath;
      if (jsonFolder) requestBody.json_folder = jsonFolder;

      const response = await fetch(`${API_URL}/expert/reindex`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestBody)
      });

      const data = await response.json();

      if (response.ok) {
        setToast({
          message: `[reindex complete: ${data.books_processed} books, ${data.quotes_processed} quotes in ${data.elapsed_seconds}s]`,
          visible: true
        });

        // Reload status after successful reindex
        setTimeout(() => {
          loadStatus();
        }, 1000);

        // Clear form
        setCsvPath('');
        setJsonFolder('');
      } else {
        setToast({ message: `[reindex failed: ${data.detail}]`, visible: true });
      }
    } catch (error) {
      console.error('Reindex error:', error);
      setToast({ message: '[reindex failed - connection error]', visible: true });
    } finally {
      setLoading(false);
      setTimeout(() => setToast({ message: '', visible: false }), 4000);
    }
  };

  return (
    <div className="min-h-screen bg-white text-black font-mono p-4 max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-8 pb-6 border-b-2 border-black">
        <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-4">
          <div>
            <h1 className="text-2xl font-bold mb-2">DATA MANAGEMENT</h1>
            <p className="text-gray-600 italic">Import and export your bibliography and quotes data</p>
            <p className="text-xs text-red-600 font-mono mt-1">API: {API_URL}</p>
          </div>

          <div className="flex flex-wrap gap-2">
            <a
              href="/"
              className="text-sm px-3 py-1 border border-blue-300 rounded hover:bg-blue-50 transition-colors text-blue-700"
            >
              ← Back to Search
            </a>
            <a
              href="/tuning"
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm px-3 py-1 border border-green-300 rounded hover:bg-green-50 transition-colors text-green-700"
            >
              Tuning Interface
            </a>
          </div>
        </div>
      </div>

      {/* Current Status */}
      {status && (
        <div className="mb-8">
          <h2 className="text-xl font-bold mb-4">Current Database Status</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
            <StatusCard
              title="Books"
              value={status.books_count?.toLocaleString() || '0'}
              description="Bibliography entries"
              color="blue"
            />
            <StatusCard
              title="Quotes"
              value={status.quotes_count?.toLocaleString() || '0'}
              description="Searchable quotes"
              color="green"
            />
            <StatusCard
              title="Database Size"
              value={`${status.database_size_mb || '0'} MB`}
              description="Storage used"
              color="orange"
            />
            <StatusCard
              title="Status"
              value={status.database_exists ? "Ready" : "Missing"}
              description="Search index state"
              color={status.database_exists ? "green" : "red"}
            />
          </div>
          <div className="text-sm text-gray-600 italic">
            {status.message}
          </div>
        </div>
      )}

      {/* Export Data Section */}
      <div className="mb-8">
        <h2 className="text-xl font-bold mb-4">Export Database</h2>
        <div className="bg-blue-50 border border-blue-300 rounded p-4">
          <div className="flex items-start gap-3 mb-4">
            <span className="text-blue-600 font-bold">💾</span>
            <div className="text-sm text-blue-800 flex-1">
              <div className="font-semibold mb-1">Export Your Complete Database</div>
              <p>Download all books and quotes (with edits applied) as a ZIP file containing CSV and JSON files. This export can be used as a backup or to import into another instance.</p>
            </div>
          </div>
          <a
            href="/api/admin/export"
            download
            className="inline-block px-6 py-3 bg-green-600 text-white rounded hover:bg-green-700 transition-colors font-bold"
          >
            Export Database (ZIP)
          </a>
          <p className="text-xs text-gray-600 mt-2">
            Includes: data/biblio/FINAL_BIBLIO_ATLANTA.csv + data/extracts/*.json
          </p>
        </div>
      </div>

      {/* Load New Data Form */}
      <div className="mb-8">
        <h2 className="text-xl font-bold mb-4">Import New Data</h2>

        <div className="bg-yellow-50 border border-yellow-300 rounded p-4 mb-6">
          <div className="flex items-start gap-3">
            <span className="text-yellow-600 font-bold">⚠️</span>
            <div className="text-sm text-yellow-800">
              <div className="font-semibold mb-1">Warning: Complete Database Replacement</div>
              <p>This operation will completely replace all existing data. The current database will be dropped and recreated with the new data you specify.</p>
            </div>
          </div>
        </div>

        <div className="space-y-6">
          {/* CSV Input */}
          <div>
            <label className="block text-sm font-bold mb-2">CSV File Path (Books Metadata)</label>
            <input
              type="text"
              value={csvPath}
              onChange={(e) => setCsvPath(e.target.value)}
              placeholder="/Users/username/data/bibliography.csv"
              className="w-full px-3 py-2 border border-gray-300 rounded text-sm font-mono focus:ring-2 focus:ring-blue-300 focus:border-blue-300"
            />
            <div className="mt-2 text-xs text-gray-600">
              <div className="font-semibold mb-1">Expected CSV columns:</div>
              <div className="font-mono">title, authors, year, publisher, journal, doi, isbn, themes, keywords, summary, iso690</div>
            </div>
          </div>

          {/* JSON Input */}
          <div>
            <label className="block text-sm font-bold mb-2">JSON Folder Path (Quotes)</label>
            <input
              type="text"
              value={jsonFolder}
              onChange={(e) => setJsonFolder(e.target.value)}
              placeholder="/Users/username/data/extracts"
              className="w-full px-3 py-2 border border-gray-300 rounded text-sm font-mono focus:ring-2 focus:ring-blue-300 focus:border-blue-300"
            />
            <div className="mt-2 text-xs text-gray-600">
              <div className="font-semibold mb-1">Expected JSON structure:</div>
              <pre className="font-mono text-xs bg-gray-100 p-2 rounded mt-1 overflow-x-auto">
{`{
  "metadata": {
    "title": "Book Title",
    "authors": "Author Names",
    "year": 2023
  },
  "quotes": [
    {
      "text": "Quote content...",
      "page": 42,
      "keywords": "keywords"
    }
  ]
}`}
              </pre>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex flex-col sm:flex-row gap-3">
            <button
              onClick={handleReindex}
              disabled={loading || (!csvPath && !jsonFolder)}
              className="px-6 py-3 bg-red-600 text-white rounded hover:bg-red-700 disabled:bg-gray-400 transition-colors font-bold flex-1 sm:flex-none"
            >
              {loading ? 'Processing...' : 'Start Complete Reindex'}
            </button>

            <button
              onClick={() => {
                setCsvPath('');
                setJsonFolder('');
              }}
              className="px-6 py-3 border border-gray-300 text-gray-700 rounded hover:bg-gray-50 transition-colors flex-1 sm:flex-none"
            >
              Clear Form
            </button>

            <button
              onClick={loadStatus}
              className="px-6 py-3 border border-blue-300 text-blue-700 rounded hover:bg-blue-50 transition-colors flex-1 sm:flex-none"
            >
              Refresh Status
            </button>
          </div>
        </div>
      </div>

      {/* Documentation */}
      <div className="border-t-2 border-gray-200 pt-6">
        <h3 className="text-lg font-bold mb-3">Process Overview</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-sm">
          <div>
            <h4 className="font-semibold mb-2">What happens during reindex:</h4>
            <ol className="list-decimal list-inside space-y-1 text-gray-700">
              <li>Validate file paths exist</li>
              <li>Drop existing database tables</li>
              <li>Recreate schema with FTS5 index</li>
              <li>Import CSV data into books table</li>
              <li>Import JSON data into quotes table</li>
              <li>Rebuild full-text search index</li>
            </ol>
          </div>
          <div>
            <h4 className="font-semibold mb-2">Requirements:</h4>
            <ul className="list-disc list-inside space-y-1 text-gray-700">
              <li>Specify at least one file path</li>
              <li>Files must be accessible to the server</li>
              <li>CSV must have proper column headers</li>
              <li>JSON files must follow expected structure</li>
              <li>Process may take several minutes for large datasets</li>
            </ul>
          </div>
        </div>
      </div>

      <Toast message={toast.message} visible={toast.visible} />
    </div>
  );
};

export default ReloadApp;