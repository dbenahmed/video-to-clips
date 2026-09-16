/**
 * Main Application Shell & Routing
 * ================================
 * Configures client-side routing via React Router DOM.
 * Follows separation of concerns with a consistent Navbar layout and modular page views.
 */

import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Navbar from './components/Navbar';
import IngestionPage from './pages/IngestionPage';
import PipelineOptionsPage from './pages/PipelineOptionsPage';
import EditorPage from './pages/EditorPage';
import NotFoundPage from './pages/NotFoundPage';
import './App.css';

export default function App() {
  return (
    <BrowserRouter>
      <div className="app-container">
        <Navbar />
        <main className="main-content">
          <Routes>
            <Route path="/" element={<IngestionPage />} />
            <Route path="/uploaded/:savedFilename" element={<IngestionPage />} />
            <Route path="/pipeline/:savedFilename" element={<PipelineOptionsPage />} />
            <Route path="/editor/:savedFilename" element={<EditorPage />} />
            {/* Future milestones can easily add:
                <Route path="/editor/:id" element={<EditorPage />} />
                <Route path="/export/:id" element={<ExportPage />} />
            */}
            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
