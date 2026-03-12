import { BrowserRouter, Routes, Route } from 'react-router-dom';
import ErrorBoundary from './components/common/ErrorBoundary';
import MainLayout from './components/layout/MainLayout';
import AgentStatusPage from './components/agents/AgentStatusPage';

export default function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<MainLayout />} />
          <Route path="/agents" element={<AgentStatusPage />} />
        </Routes>
      </BrowserRouter>
    </ErrorBoundary>
  );
}
