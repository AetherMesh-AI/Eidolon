import { Activity, BookOpen, Boxes, Command, FolderOpen, Settings, Target } from 'lucide-react'
import type { ReactNode } from 'react'
import { NavLink } from 'react-router'

import './eidolon.css'

const destinations = [
  { to: '/home', label: 'Command', icon: Command },
  { to: '/objectives', label: 'Objectives', icon: Target },
  { to: '/organization', label: 'Organization', icon: Boxes },
  { to: '/artifacts', label: 'Workspace', icon: FolderOpen },
  { to: '/activity', label: 'Activity', icon: Activity },
  { to: '/knowledge', label: 'Knowledge', icon: BookOpen },
  { to: '/settings', label: 'Settings', icon: Settings }
]

/** The canonical session tree is retained, not re-created or synthesized. */
export function OrganizationRail({ sessions, onNavigate }: { sessions: ReactNode; onNavigate?: (to: string) => void }) {
  return <aside className="eidolon eid-rail" aria-label="Eidolon navigation">
    <div className="eid-brand"><span aria-hidden="true">◈</span>EIDOLON</div>
    <nav aria-label="Primary">{destinations.map(({ to, label, icon: Icon }) => <NavLink to={to} key={to} title={label} onClick={event => { if (onNavigate && !event.metaKey && !event.ctrlKey && !event.shiftKey && !event.altKey) { event.preventDefault(); onNavigate(to) } }}><Icon size={16} aria-hidden="true" /><span>{label}</span></NavLink>)}</nav>
    <section aria-label="Agent messages"><h2>Messages</h2><p>One persistent conversation per agent.</p><div className="eid-session-tree">{sessions}</div></section>
    <div className="eid-rail-footer">Organization · Local prototype<br />Messages use canonical profile Bot Chats.</div>
  </aside>
}
