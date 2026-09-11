import { useState } from 'react'
import { Link } from 'react-router'
import type { ActivityEvent, OrganizationSnapshot } from './types'
import { Inspector } from './inspector'
import { AgentAvatar } from './avatar'

const categories = { assignment: 'Assignments', decision: 'Decisions', tool: 'Tools', file: 'Files', review: 'Reviews', system: 'System' } as const
const eventCategory: Record<ActivityEvent['kind'], keyof typeof categories> = {
 delegation: 'assignment', completion: 'assignment', decision: 'decision', tool: 'tool', file: 'file',
 approval: 'review', blocker: 'review', review: 'review', planning: 'system', knowledge: 'system', message: 'system', system: 'system',
}

export function Activity({ snapshot, objectiveId }: { snapshot: OrganizationSnapshot; objectiveId?: string }) {
 const [query, setQuery] = useState('')
 const [kind, setKind] = useState('all')
 const [objective, setObjective] = useState('all')
 const [agent, setAgent] = useState('all')
 const [selected, setSelected] = useState<string | null>(null)
 const items = snapshot.activity.filter(item =>
   (!objectiveId || item.objectiveId === objectiveId) && (kind === 'all' || eventCategory[item.kind] === kind) && (objective === 'all' || item.objectiveId === objective) &&
   (agent === 'all' || item.agentId === agent) && item.text.toLowerCase().includes(query.toLowerCase()))
 const event = items.find(item => item.id === selected)
 return <><h2>Coordination timeline</h2>
  <p>Human-readable coordination, decisions and outcomes. Prototype records are not live execution logs.</p>
  <div className="eid-toolbar">
   <input type="search" aria-label="Search activity" placeholder="Search events" value={query} onChange={e => setQuery(e.target.value)} />
   <select aria-label="Event type" value={kind} onChange={e => setKind(e.target.value)}><option value="all">All</option>{Object.entries(categories).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select>
   <select aria-label="Activity objective" disabled={!!objectiveId} value={objectiveId || objective} onChange={e => setObjective(e.target.value)}><option value="all">All objectives</option>{snapshot.objectives.map(item => <option key={item.id} value={item.id}>{item.title}</option>)}</select>
   <select aria-label="Activity agent" value={agent} onChange={e => setAgent(e.target.value)}><option value="all">All agents</option>{snapshot.agents.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select>
  </div>
  {items.length ? <ol className="eid-list">{items.map(item => <li key={item.id}>
   <button className="eid-row" style={{ width: '100%', textAlign: 'left' }} aria-label={`Inspect event: ${item.text}`} onClick={() => setSelected(item.id)}>
    <AgentAvatar name={snapshot.agents.find(a => a.id === item.agentId)?.name || 'Organization'} /><span><small>{categories[eventCategory[item.kind]]} · {item.provenance === 'fictional' ? 'Fictional example' : 'Local prototype'}</small><strong>{item.text}</strong><small>{item.agentId ? snapshot.agents.find(a => a.id === item.agentId)?.name || 'Unlinked agent' : 'Organization'}{item.objectiveId ? ` · ${snapshot.objectives.find(o => o.id === item.objectiveId)?.title || 'Unlinked objective'}` : ''}</small></span>
    <time dateTime={item.timestamp}>{new Date(item.timestamp).toLocaleString()}</time>
   </button>
  </li>)}</ol> : <div className="eid-empty"><h2>{snapshot.activity.length ? 'No matching events' : 'No organization events yet'}</h2><p>Create an objective to record a local planning event.</p></div>}
  <p><Link to="/processes">Inspect live process logs →</Link></p>
  {event && <Inspector kind="event" title={event.text} onClose={() => setSelected(null)}>
   <p className="eid-eyebrow">{event.provenance === 'fictional' ? 'Fictional example · Not live' : 'Local prototype event · Not live'}</p><dl><dt>Category</dt><dd>{categories[eventCategory[event.kind]]}</dd><dt>Event type</dt><dd>{event.kind}</dd><dt>Recorded</dt><dd><time dateTime={event.timestamp}>{new Date(event.timestamp).toLocaleString()}</time></dd><dt>Agent</dt><dd>{snapshot.agents.find(item => item.id === event.agentId)?.name || 'No agent linked'}</dd></dl>
   {event.description && <><h3>Observable details</h3><p>{event.description}</p></>}
   {event.objectiveId && <Link to={`/objectives/${event.objectiveId}`}>Open objective</Link>}
   <h3>Diagnostic context</h3><p>No runtime log or process identifier is attached. This record comes from the local prototype adapter.</p>
  </Inspector>}
 </>
}
