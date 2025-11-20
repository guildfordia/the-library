import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import App from './App';
import TuningApp from './TuningApp';
import ReloadApp from './ReloadApp';
import './index.css';

const root = ReactDOM.createRoot(document.getElementById('root'));

root.render(
  <React.StrictMode>
    <Router>
      <Routes>
        <Route path="/" element={<App />} />
        <Route path="/tuning" element={<TuningApp />} />
        <Route path="/data" element={<ReloadApp />} />
        <Route path="/reload" element={<ReloadApp />} /> {/* Keep old route for backwards compatibility */}
      </Routes>
    </Router>
  </React.StrictMode>
);