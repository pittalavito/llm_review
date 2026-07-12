/**
 * App shell: header + sidebar navigation + routed content.
 * Mirrors ui/index.html structure and classes so the existing CSS applies.
 */
import { useEffect } from 'react';
import { NavLink, Outlet, useLocation } from 'react-router-dom';

interface NavEntry {
  to: string;
  icon: string;
  label: string;
}

const DEV_ENTRIES: NavEntry[] = [
  { to: '/health', icon: '§', label: 'System Status' },
  { to: '/test-llm', icon: '✎', label: 'Test LLM' },
  { to: '/test-agent', icon: 'A', label: 'Test Agent' },
  { to: '/test-rag', icon: 'R', label: 'Test RAG' },
  { to: '/swagger', icon: '⌘', label: 'API Docs' },
  { to: '/redis', icon: '▤', label: 'Redis' },
];

const PIPELINE_ENTRIES: NavEntry[] = [
  { to: '/prompts', icon: '✏', label: 'Prompt Versions' },
  { to: '/graph-run', icon: '▶', label: 'Graph Run' },
  { to: '/storico', icon: '⏱', label: 'Storico Review' },
  { to: '/comparison', icon: '⇄', label: 'Confronto Review' },
  { to: '/backup', icon: '⬇', label: 'Backup DB' },
];

function NavItem({ entry }: { entry: NavEntry }) {
  return (
    <NavLink to={entry.to} style={{ textDecoration: 'none', color: 'inherit' }}>
      {({ isActive }) => (
        <li className={`nav__item${isActive ? ' nav__item--active' : ''}`}>
          <span className="nav__icon">{entry.icon}</span>
          <span className="nav__label">{entry.label}</span>
        </li>
      )}
    </NavLink>
  );
}

export default function AppLayout() {
  const location = useLocation();

  useEffect(() => {
    const entry = [...DEV_ENTRIES, ...PIPELINE_ENTRIES].find((e) => e.to === location.pathname);
    document.title = entry
      ? `${entry.label} — LLM Review`
      : 'LLM Review — Academic Review Platform';
  }, [location.pathname]);

  return (
    <>
      <header className="header">
        <h1 className="header__title">LLM Review</h1>
        <p className="header__subtitle">Academic Peer Review Platform — React</p>
      </header>

      <div className="app-body">
        <aside className="sidebar">
          <nav>
            <ul className="nav__list">
              <li className="nav__group-title">Dev Controller</li>
              {DEV_ENTRIES.map((entry) => <NavItem key={entry.to} entry={entry} />)}
              <li className="nav__group-title">Pipeline</li>
              {PIPELINE_ENTRIES.map((entry) => <NavItem key={entry.to} entry={entry} />)}
            </ul>
          </nav>
        </aside>

        <main className="content" id="content-area">
          <Outlet />
        </main>
      </div>
    </>
  );
}
