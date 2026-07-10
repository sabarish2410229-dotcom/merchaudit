import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import './Layout.css';

const NAV_ITEMS = [
  { to: '/merchants', label: 'Merchants', icon: '◈' },
  { to: '/reports', label: 'Reports', icon: '▤' },
];

export default function Layout({ children }) {
  const { user, signOut } = useAuth();
  const navigate = useNavigate();

  function handleSignOut() {
    signOut();
    navigate('/login');
  }

  return (
    <div className="shell">
      <aside className="shell__sidebar">
        <div className="shell__brand">
          <span className="shell__brand-mark">MA</span>
          <div>
            <div className="shell__brand-name">MerchAudit</div>
            <div className="shell__brand-sub">Underwriting desk</div>
          </div>
        </div>

        <nav className="shell__nav">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                'shell__nav-item' + (isActive ? ' shell__nav-item--active' : '')
              }
            >
              <span className="shell__nav-icon">{item.icon}</span>
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="shell__footer">
          {user && (
            <>
              <div className="shell__user">
                <div className="shell__user-email">{user.email}</div>
                <div className="shell__user-role">{user.role}</div>
              </div>
              <button className="shell__signout" onClick={handleSignOut}>
                Sign out
              </button>
            </>
          )}
        </div>
      </aside>

      <main className="shell__main">{children}</main>
    </div>
  );
}
