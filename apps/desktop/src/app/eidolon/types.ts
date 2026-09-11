export const objectiveStatusLabels = {
  planning: 'Planning', active: 'Active', waiting: 'Waiting', needs_input: 'Needs Input',
  blocked: 'Blocked', completed: 'Completed', paused: 'Paused', archived: 'Archived',
} as const
export type ObjectiveStatus = keyof typeof objectiveStatusLabels
export type WorkStatus = 'working' | 'active' | 'thinking' | 'executing' | 'reviewing' | 'needs_input' | 'idle' | 'waiting' | 'review' | 'offline'
export interface ObjectiveMetadata {
  description?: string
  priority?: 'low' | 'normal' | 'high' | 'P5' | 'P4' | 'P3' | 'P2' | 'P1'
  agentId?: string
  progress?: number
  phase?: string
  milestone?: string
  autonomyIntent?: string
}
export interface Objective extends ObjectiveMetadata {
  id: string
  title: string
  description: string
  status: ObjectiveStatus
  source: 'prototype'
  createdAt: string
  ownerId: string
  sessionId?: string
  result?: string
}
export interface OrganizationAgent {
  id: string
  name: string
  role: string
  team?: string
  managerId?: string
  responsibilities: string[]
  capabilities: string[]
  status: WorkStatus
  summary: string
  model?: string
  context?: { used?: number; capacity?: number }
  tools?: string[]
  profileName?: string
  objectiveId?: string
}
export interface OrganizationTask {
  id: string
  objectiveId: string
  title: string
  ownerId: string
  status: 'queued' | 'working' | 'blocked' | 'review' | 'completed'
  assignedById?: string
  priority?: 'low' | 'normal' | 'high' | 'P5' | 'P4' | 'P3' | 'P2' | 'P1'
  agentId?: string
  review?: 'required' | 'not_required' | 'approved'
  inputs?: string[]
  results?: string[]
  dependsOn: string[]
}
export interface ActivityEvent {
  id: string
  objectiveId?: string
  agentId?: string
  kind: 'planning' | 'delegation' | 'completion' | 'blocker' | 'approval' | 'knowledge' | 'message' | 'decision' | 'tool' | 'file' | 'review' | 'system'
  provenance?: 'fictional'
  description?: string
  text: string
  timestamp: string
  source: 'prototype'
}
export interface KnowledgeItem {
  id: string
  title: string
  body: string
  kind: 'memory' | 'document' | 'artifact'
  objectiveId?: string
}
export interface OrganizationDecision {
  id: string
  objectiveId: string
  title: string
  summary: string
  status: 'pending' | 'approved' | 'rejected' | 'recorded'
}
export interface OrganizationSnapshot {
  decisions?: OrganizationDecision[]
  objectives: Objective[]
  agents: OrganizationAgent[]
  tasks: OrganizationTask[]
  activity: ActivityEvent[]
  knowledge: KnowledgeItem[]
}
export interface OrganizationAdapter {
  readonly mode: 'prototype'
  getSnapshot: () => OrganizationSnapshot
  subscribe: (listener: () => void) => () => void
  createObjective: (title: string, metadata?: ObjectiveMetadata) => Objective
  updateObjectiveMetadata(id: string, metadata: ObjectiveMetadata): void
  setObjectiveStatus(id: string, status: ObjectiveStatus): void
  recordOutcome(id: string, summary: string): void
  resolveDecision(id: string, status: 'approved' | 'rejected'): void
  loadDemo(): void
  reset(): void
}
