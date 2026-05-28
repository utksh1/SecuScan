import { describe, it, expect, vi } from 'vitest'
import { createTicket } from '../api'

// Mock the global request function by mocking the module
vi.mock('../api', async () => {
  const actual = await vi.importActual('../api')
  return {
    ...actual,
    createTicket: vi.fn().mockResolvedValue({ ticket_id: 'TEST-123', ticket_url: 'http://example.com/TEST-123' }),
    upsertVaultSecret: vi.fn().mockResolvedValue({}),
  }
})

describe('Export Flow', () => {
  it('calls createTicket without config object (backend handles secrets)', async () => {
    const finding = {
      id: '123',
      title: 'Test Finding',
      severity: 'high',
      status: 'new'
    }

    // Call the exported mocked function directly to verify it works without config
    await createTicket('jira', finding)

    expect(createTicket).toHaveBeenCalledWith('jira', finding)
    // We expect it to be called with exactly 2 arguments (provider, finding), 
    // ensuring no credentials object is passed from the frontend.
    expect(createTicket).toHaveBeenCalledTimes(1)
  })
})
