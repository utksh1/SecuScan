import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import TaskCard from '../TaskCard'

describe('TaskCard', () => {
  const mockTask = {
    task_id: '123-abc',
    plugin_name: 'Nmap Scanner',
    status: 'completed',
    preset: 'quick',
    created_at: '2023-10-15T10:00:00Z',
    finished_at: '2023-10-15T10:05:00Z'
  }

  it('renders task details correctly', () => {
    render(
      <MemoryRouter>
        <TaskCard task={mockTask} />
      </MemoryRouter>
    )

    expect(screen.getByText('Nmap Scanner')).toBeInTheDocument()
    expect(screen.getByText(/123-abc/i)).toBeInTheDocument()
    expect(screen.getByText('COMPLETED')).toBeInTheDocument()
    expect(screen.getByText(/quick/i)).toBeInTheDocument()
  })

  it('renders a link to the task details page', () => {
    render(
      <MemoryRouter>
        <TaskCard task={mockTask} />
      </MemoryRouter>
    )

    const link = screen.getByRole('link')
    expect(link).toHaveAttribute('href', '/task/123-abc')
  })
})
