import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Box } from '@mui/material';
import Layout from './components/Layout/Layout';
import Workbench from './pages/Workbench/Workbench';

// Placeholder components
import History from './pages/History/History';

function App() {
  return (
    <Router>
      <Box className="aurora-bg full-height">
        <Layout>
          <Routes>
            <Route path="/" element={<Navigate to="/workbench" replace />} />
            <Route path="/workbench" element={<Workbench />} />
            <Route path="/history" element={<History />} />
          </Routes>
        </Layout>
      </Box>
    </Router>
  );
}

export default App;
