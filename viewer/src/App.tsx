import { Routes, Route, NavLink } from 'react-router-dom';
import Home from './pages/Home';
import Search from './pages/Search';
import ShowDetail from './pages/ShowDetail';

function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div>
      <nav className="nav">
        <NavLink to="/" style={{ fontWeight: 'bold', fontSize: '1.25rem', color: 'var(--primary)' }}>Peblo TV</NavLink>
        <NavLink to="/">Home</NavLink>
        <NavLink to="/search">Search</NavLink>
      </nav>
      {children}
    </div>
  );
}

function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout><Home /></Layout>} />
      <Route path="/search" element={<Layout><Search /></Layout>} />
      <Route path="/shows/:id" element={<Layout><ShowDetail /></Layout>} />
    </Routes>
  );
}

export default App;
