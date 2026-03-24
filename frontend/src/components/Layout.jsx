import { NavLink } from 'react-router-dom'
import { useApp } from '../context/AppContext'

export default function Layout({ children }) {
  const { plugins, loading, error } = useApp()

  return (
    <div className="app">
      <aside className="sidebar">
        <h2 style={{ margin: '0 0 16px 0', fontSize: '20px' }}>🔒 SecuScan</h2>
        
        <nav style={{ marginBottom: '24px' }}>
          <NavLink 
            to="/scanner" 
            className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}
            style={{ display: 'block', padding: '8px', textDecoration: 'none', color: '#111' }}
          >
            🔍 Scanner
          </NavLink>
          <NavLink 
            to="/history"
            className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}
            style={{ display: 'block', padding: '8px', textDecoration: 'none', color: '#111' }}
          >
            📋 History
          </NavLink>
          <NavLink 
            to="/settings"
            className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}
            style={{ display: 'block', padding: '8px', textDecoration: 'none', color: '#111' }}
          >
            ⚙️ Settings
          </NavLink>
        </nav>

        {loading && <p>Loading plugins...</p>}
        {error && <p style={{ color: 'red', fontSize: '14px' }}>Error: {error}</p>}
        
        {!loading && !error && (
          <>
            <h3 style={{ fontSize: '14px', margin: '0 0 8px 0', color: '#6b7280' }}>PLUGINS</h3>
            <ul className="list">
              {plugins.map((plugin) => (
                <li key={plugin.id}>
                  <NavLink
                    to={`/scanner/${plugin.id}`}
                    className={({ isActive }) => isActive ? 'active' : ''}
                    style={{ textDecoration: 'none', color: 'inherit', display: 'block' }}
                  >
                    <div style={{ fontSize: '14px', fontWeight: '600' }}>{plugin.name}</div>
                    <div style={{ fontSize: '12px', color: '#6b7280', marginTop: '2px' }}>
                      {plugin.description}
                    </div>
                  </NavLink>
                </li>
              ))}
            </ul>
          </>
        )}
      </aside>
      
      <main className="main">{children}</main>
    </div>
  )
}
