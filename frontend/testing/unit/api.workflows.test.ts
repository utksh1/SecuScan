import { afterEach, describe, expect, it, vi } from 'vitest'
import { createWorkflow, getWorkflows, runWorkflow, updateWorkflow } from '../../src/api'

function mockJsonResponse(body: unknown) {
  return Promise.resolve({
    ok: true,
    json: () => Promise.resolve(body),
  } as Response)
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('workflow API helpers', () => {
  it('normalizes backend workflow list responses', async () => {
    vi.stubGlobal('fetch', vi.fn().mockReturnValue(mockJsonResponse({
      workflows: [
        {
          id: 'wf-001',
          name: 'Nightly Scan',
          schedule_seconds: '3600',
          enabled: 1,
          steps_json: '[{"plugin_id":"nmap","inputs":{}}]',
          last_run_at: null,
        },
      ],
      total: 1,
    })))

    const workflows = await getWorkflows()

    expect(workflows).toEqual([
      {
        id: 'wf-001',
        name: 'Nightly Scan',
        schedule_seconds: 3600,
        enabled: true,
        steps: [{ plugin_id: 'nmap', inputs: {} }],
        last_run_at: null,
        queued_task_ids: [],
        created_at: undefined,
      },
    ])
  })

  it('sends schedule_seconds when creating workflows', async () => {
    const fetchMock = vi.fn().mockReturnValue(mockJsonResponse({
      id: 'wf-002',
      name: 'Hourly Scan',
      schedule_seconds: 3600,
      enabled: true,
      steps: [{ plugin_id: 'http_inspector', inputs: {} }],
    }))
    vi.stubGlobal('fetch', fetchMock)

    await createWorkflow({
      name: 'Hourly Scan',
      schedule_seconds: 3600,
      enabled: true,
      steps: [{ plugin_id: 'http_inspector', inputs: {} }],
    })

    const [, init] = fetchMock.mock.calls[0]
    expect(JSON.parse(init.body)).toMatchObject({
      name: 'Hourly Scan',
      schedule_seconds: 3600,
      enabled: true,
    })
  })

  it('normalizes queued_tasks from workflow run responses', async () => {
    vi.stubGlobal('fetch', vi.fn().mockReturnValue(mockJsonResponse({
      workflow_id: 'wf-001',
      queued_tasks: ['task-001'],
    })))

    await expect(runWorkflow('wf-001')).resolves.toEqual({
      queued_task_ids: ['task-001'],
    })
  })

  it('normalizes updated workflow responses', async () => {
    vi.stubGlobal('fetch', vi.fn().mockReturnValue(mockJsonResponse({
      id: 'wf-001',
      name: 'Nightly Scan',
      schedule_seconds: 7200,
      enabled: 0,
      steps_json: '[]',
    })))

    await expect(updateWorkflow('wf-001', { enabled: false })).resolves.toMatchObject({
      id: 'wf-001',
      schedule_seconds: 7200,
      enabled: false,
      steps: [],
    })
  })
})
