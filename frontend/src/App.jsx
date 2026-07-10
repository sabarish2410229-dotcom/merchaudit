import { Navigate, Route, Routes } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import Login from './pages/Login';
import Register from './pages/Register';
import Merchants from './pages/Merchants';
import Reports from './pages/Reports';

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route
          path="/merchants"
          element={
            <ProtectedRoute>
              <Merchants />
            </ProtectedRoute>
          }
        />
        <Route
          path="/reports"
          element={
            <ProtectedRoute>
              <Reports />
            </ProtectedRoute>
          }
        />
        <Route path="/" element={<Navigate to="/merchants" replace />} />
        <Route path="*" element={<Navigate to="/merchants" replace />} />
      </Routes>
    </AuthProvider>
  );
}
