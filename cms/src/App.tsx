import { Routes, Route, Navigate, NavLink } from 'react-router-dom';
import { useAuth } from './contexts/AuthContext';
import { LogOut } from 'lucide-react';
import Login from './pages/Login';
import ShowsList from './pages/ShowsList';
import ShowEditor from './pages/ShowEditor';
import Publish from './pages/Publish';

function ProtectedRoute({ children, requireAdmin }: { children: React.ReactNode, requireAdmin?: boolean }) {
  const { user, loading } = useAuth();
  if (loading) return <div>Loading...</div>;
  if (!user) return <Navigate to="/login" replace />;
  if (requireAdmin && user.role !== 'admin') return <Navigate to="/" replace />;
  return children;
}

function Layout({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuth();
  
  return (
    <div className="layout">
      <div className="sidebar">
        <div style={{ marginBottom: '2rem', fontWeight: 'bold', fontSize: '1.25rem' }}>Peblo TV CMS</div>
        <nav>
          <NavLink to="/" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`} end>Shows</NavLink>
          {user?.role === 'admin' && (
            <NavLink to="/publish" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>Publish</NavLink>
          )}
        </nav>
        <div style={{ position: 'absolute', bottom: '2rem' }}>
          <div style={{ marginBottom: '1rem', color: 'var(--text-muted)' }}>{user?.email}<br/><small>{user?.role}</small></div>
          <button className="btn btn-secondary" onClick={logout}>
            <LogOut size={16} style={{ marginRight: '0.5rem' }} /> Logout
          </button>
        </div>
      </div>
      <div className="main">
        {children}
      </div>
    </div>
  );
}

function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/" element={<ProtectedRoute><Layout><ShowsList /></Layout></ProtectedRoute>} />
      <Route path="/shows/new" element={<ProtectedRoute><Layout><ShowEditor /></Layout></ProtectedRoute>} />
      <Route path="/shows/:id" element={<ProtectedRoute><Layout><ShowEditor /></Layout></ProtectedRoute>} />
      <Route path="/publish" element={<ProtectedRoute requireAdmin><Layout><Publish /></Layout></ProtectedRoute>} />
    </Routes>
  );
}

export default App;
