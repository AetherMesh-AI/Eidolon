import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { expect, it } from 'vitest'
import { WorkGraph } from './work-graph'
import { demoSnapshot } from './demo'
it('shows dependency and task inspection without claiming runtime execution', () => {
 const snapshot = demoSnapshot()
 render(<MemoryRouter><WorkGraph snapshot={snapshot} objectiveId="demo-identity" /></MemoryRouter>)
 fireEvent.click(screen.getByRole('button', { name: /Inspect task: Implement/ }))
 expect(screen.getByRole('complementary', { name: 'Task details' })).toBeTruthy()
 expect(screen.getByText('No runtime session linked')).toBeTruthy()
})
