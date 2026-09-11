export function AgentAvatar({ name }: { name: string }) {
 return <span className="eid-avatar" role="img" aria-label={`${name} avatar`}>{name.trim().split(/\s+/).slice(0, 2).map(part => part[0]).join('').toUpperCase() || '?'}</span>
}
