import ErrorBoundary from './components/common/ErrorBoundary';
import MainLayout from './components/layout/MainLayout';

export default function App() {
  return (
    <ErrorBoundary>
      <MainLayout />
    </ErrorBoundary>
  );
}
