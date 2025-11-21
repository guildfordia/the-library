import React, { useState, useEffect } from 'react';
import './index.css';

const API_URL = process.env.REACT_APP_API_URL || '/api';

// Debug: Show what API URL is being used
console.log('TuningApp API_URL being used:', API_URL);

// Components
const Slider = ({ label, value, min, max, step, onChange, description }) => (
  <div className="mb-4">
    <div className="flex justify-between items-center mb-1">
      <label className="text-sm font-semibold text-gray-700">{label}</label>
      <span className="text-sm text-gray-500">{value}</span>
    </div>
    <input
      type="range"
      min={min}
      max={max}
      step={step}
      value={value}
      onChange={(e) => onChange(parseFloat(e.target.value))}
      className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
    />
    {description && <p className="text-xs text-gray-500 mt-1">{description}</p>}
  </div>
);

const ScoreBreakdown = ({ breakdown }) => (
  <div className="text-xs text-gray-600 mt-2 p-2 bg-gray-50 rounded border">
    <div className="font-semibold mb-1">Score Breakdown:</div>
    <div>BM25 Raw: {breakdown.bm25_raw?.toFixed(3)}</div>
    <div>BM25 Normalized: {breakdown.bm25_normalized?.toFixed(3)}</div>
    <div>Field Score: {breakdown.field_score?.toFixed(3)}</div>
    <div>Phrase Bonus: {breakdown.phrase_bonus?.toFixed(3)}</div>
    <div>Quote Boost: {breakdown.quote_boost?.toFixed(3)}</div>
    <div className="font-semibold border-t pt-1 mt-1">Final Score: {breakdown.final_score?.toFixed(3)}</div>
  </div>
);

const ResultCard = ({ result }) => (
  <div className="border border-gray-200 rounded p-3 mb-3 bg-white text-sm">
    <div className="mb-2">
      <div className="font-bold">{result.book_title || 'Unknown title'}</div>
      <div className="text-gray-600">{result.book_authors || 'Unknown author'}</div>
    </div>
    <div className="mb-2">
      <span className="font-semibold">Quote:</span> {result.quote_text}
    </div>
    {result.page && (
      <div className="text-gray-500">Page: {result.page}</div>
    )}
    <div className="font-semibold text-gray-700">Score: {result.score_breakdown?.final_score?.toFixed(3)}</div>
    <ScoreBreakdown breakdown={result.score_breakdown} />
  </div>
);

const TuningApp = () => {
  const [config, setConfig] = useState({
    bm25_weight: 1.0,
    phrase_bonus: 2.0,
    field_weights: {
      quote_text: 1.0,
      quote_keywords: 0.8,
      book_keywords: 0.7,
      themes: 0.6,
      summary: 0.5,
      book_title: 3.0,
      book_authors: 2.5,
      type: 0.4,
      publisher: 0.3,
      journal: 0.3
    }
  });


  const [currentProfile, setCurrentProfile] = useState('default');


  const [message, setMessage] = useState('');

  // Load initial configuration
  useEffect(() => {
    loadCurrentConfig();
  }, []);

  const loadCurrentConfig = async () => {
    try {
      const response = await fetch(`${API_URL}/tuning/config`);
      const data = await response.json();
      setConfig(data.config);
      setCurrentProfile(data.profile);
    } catch (error) {
      console.error('Error loading config:', error);
    }
  };


  const updateConfig = async (newConfig) => {
    try {
      await fetch(`${API_URL}/tuning/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newConfig)
      });
      setConfig(newConfig);
    } catch (error) {
      console.error('Error updating config:', error);
    }
  };

  const exportTuning = () => {
    const tuningData = {
      profile: currentProfile,
      config: config,
      exported_at: new Date().toISOString()
    };

    const blob = new Blob([JSON.stringify(tuningData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `tuning-${currentProfile}-${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    setMessage('Tuning configuration exported successfully');
  };

  const importTuning = () => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json';
    input.onchange = async (e) => {
      const file = e.target.files[0];
      if (!file) return;

      try {
        const text = await file.text();
        const tuningData = JSON.parse(text);

        // Validate the tuning data structure
        if (!tuningData.config || !tuningData.config.field_weights) {
          throw new Error('Invalid tuning file format');
        }

        // Apply the tuning configuration
        await fetch(`${API_URL}/tuning/config`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(tuningData.config)
        });

        setConfig(tuningData.config);
        setMessage('Tuning configuration imported successfully');
        setTimeout(() => setMessage(''), 3000);
      } catch (error) {
        console.error('Import error:', error);
        setMessage('Import failed: ' + error.message);
        setTimeout(() => setMessage(''), 3000);
      }
    };
    input.click();
  };

  const resetToDefaults = async () => {
    if (!window.confirm('Reset all tuning parameters to default values? This cannot be undone.')) {
      return;
    }

    const defaultConfig = {
      bm25_weight: 1.0,
      phrase_bonus: 2.0,
      field_weights: {
        quote_text: 1.0,
        quote_keywords: 0.8,
        book_keywords: 0.7,
        themes: 0.6,
        summary: 0.5,
        book_title: 3.0,
        book_authors: 2.5,
        type: 0.4,
        publisher: 0.3,
        journal: 0.3
      }
    };

    try {
      await updateConfig(defaultConfig);
      setMessage('Configuration reset to default values');
    } catch (error) {
      console.error('Error resetting to defaults:', error);
      setMessage('Error resetting configuration');
    }
  };



  return (
    <div className="min-h-screen bg-white p-4 font-mono">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-8 pb-6 border-b-2 border-black">
          <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-4">
            <div>
              <h1 className="text-2xl font-bold mb-2">TUNING INTERFACE</h1>
              <p className="text-gray-600 italic">Adjust search scoring parameters and field weights</p>
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
                href="/data"
                className="text-sm px-3 py-1 border border-green-300 rounded hover:bg-green-50 transition-colors text-green-700"
              >
                Data Management
              </a>
            </div>
          </div>
        </div>

        {message && (
          <div className="mb-4 p-3 bg-gray-100 border rounded text-sm">
            {message}
            <button
              onClick={() => setMessage('')}
              className="ml-2 text-gray-500 hover:text-gray-700"
            >
              ×
            </button>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left Column: Configuration */}
          <div className="space-y-6">
            {/* Global Weights */}
            <div className="border border-gray-200 rounded p-4">
              <h2 className="font-bold mb-4">Global Weights</h2>

              <Slider
                label="BM25 Weight"
                value={config.bm25_weight}
                min={0}
                max={5}
                step={0.1}
                onChange={(value) => updateConfig({...config, bm25_weight: value})}
                description="Weight applied to BM25 relevance scores"
              />

              <Slider
                label="Phrase Bonus"
                value={config.phrase_bonus}
                min={0}
                max={5}
                step={0.1}
                onChange={(value) => updateConfig({...config, phrase_bonus: value})}
                description="Bonus for exact phrase matches"
              />

            </div>

            {/* Field Weights */}
            <div className="border border-gray-200 rounded p-4">
              <h2 className="font-bold mb-4">Field Weights</h2>

              <Slider
                label="Book Title Weight"
                value={config.field_weights.book_title}
                min={0}
                max={5}
                step={0.1}
                onChange={(value) => updateConfig({
                  ...config,
                  field_weights: {...config.field_weights, book_title: value}
                })}
                description="Weight for book title matches"
              />

              <Slider
                label="Book Authors Weight"
                value={config.field_weights.book_authors}
                min={0}
                max={5}
                step={0.1}
                onChange={(value) => updateConfig({
                  ...config,
                  field_weights: {...config.field_weights, book_authors: value}
                })}
                description="Weight for book author matches"
              />

              <Slider
                label="Quote Text Weight"
                value={config.field_weights.quote_text}
                min={0}
                max={5}
                step={0.1}
                onChange={(value) => updateConfig({
                  ...config,
                  field_weights: {...config.field_weights, quote_text: value}
                })}
                description="Weight for quote text content"
              />

              <Slider
                label="Quote Keywords Weight"
                value={config.field_weights.quote_keywords}
                min={0}
                max={5}
                step={0.1}
                onChange={(value) => updateConfig({
                  ...config,
                  field_weights: {...config.field_weights, quote_keywords: value}
                })}
                description="Weight for keywords attached to quotes"
              />

              <Slider
                label="Book Keywords Weight"
                value={config.field_weights.book_keywords}
                min={0}
                max={5}
                step={0.1}
                onChange={(value) => updateConfig({
                  ...config,
                  field_weights: {...config.field_weights, book_keywords: value}
                })}
                description="Weight for keywords attached to books"
              />

              <Slider
                label="Themes Weight"
                value={config.field_weights.themes}
                min={0}
                max={5}
                step={0.1}
                onChange={(value) => updateConfig({
                  ...config,
                  field_weights: {...config.field_weights, themes: value}
                })}
                description="Weight for book themes"
              />

              <Slider
                label="Summary Weight"
                value={config.field_weights.summary}
                min={0}
                max={5}
                step={0.1}
                onChange={(value) => updateConfig({
                  ...config,
                  field_weights: {...config.field_weights, summary: value}
                })}
                description="Weight for book summaries"
              />

              <Slider
                label="Type Weight"
                value={config.field_weights.type}
                min={0}
                max={5}
                step={0.1}
                onChange={(value) => updateConfig({
                  ...config,
                  field_weights: {...config.field_weights, type: value}
                })}
                description="Weight for book type/category"
              />

              <Slider
                label="Publisher Weight"
                value={config.field_weights.publisher}
                min={0}
                max={5}
                step={0.1}
                onChange={(value) => updateConfig({
                  ...config,
                  field_weights: {...config.field_weights, publisher: value}
                })}
                description="Weight for book publisher"
              />

              <Slider
                label="Journal Weight"
                value={config.field_weights.journal}
                min={0}
                max={5}
                step={0.1}
                onChange={(value) => updateConfig({
                  ...config,
                  field_weights: {...config.field_weights, journal: value}
                })}
                description="Weight for journal names"
              />
            </div>


          </div>

          {/* Right Column: Export and Actions */}
          <div className="space-y-6">
            {/* Import */}
            <div className="border border-gray-200 rounded p-4">
              <h2 className="font-bold mb-4">Import Tuning</h2>
              <p className="text-sm text-gray-600 mb-4">
                Import a previously exported tuning configuration JSON file.
              </p>
              <button
                onClick={importTuning}
                className="px-4 py-2 text-sm border border-gray-200 rounded hover:bg-gray-50 bg-green-50 border-green-200 text-green-700"
              >
                Import Configuration
              </button>
            </div>

            {/* Export */}
            <div className="border border-gray-200 rounded p-4">
              <h2 className="font-bold mb-4">Export Tuning</h2>
              <p className="text-sm text-gray-600 mb-4">
                Export your current tuning configuration as a JSON file for backup or sharing.
              </p>
              <button
                onClick={exportTuning}
                className="px-4 py-2 text-sm border border-gray-200 rounded hover:bg-gray-50 bg-blue-50 border-blue-200 text-blue-700"
              >
                Export Current Configuration
              </button>
            </div>

            {/* Reset to Defaults */}
            <div className="border border-gray-200 rounded p-4">
              <h2 className="font-bold mb-4">Reset Configuration</h2>
              <p className="text-sm text-gray-600 mb-4">
                Reset all tuning parameters to their default values. This will restore all weights to their original settings.
              </p>
              <button
                onClick={resetToDefaults}
                className="px-4 py-2 text-sm border border-red-300 rounded hover:bg-red-50 bg-red-50 border-red-300 text-red-700"
              >
                Reset to Default Values
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TuningApp;