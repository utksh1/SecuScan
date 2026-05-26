import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { OfflineQueueProvider, useOfflineQueue } from '../../../src/components/OfflineQueueContext'
import * as offlineQueue from '../../../src/services/offlineQueue'

function TestConsumer() {
  const { isOnline, pendingCount, queue, enqueue, retryAll, remove, clear } = useOfflineQueue()
  return (
    <div>
      <span data-testid="online">{String(isOnline)}</span>
      <span data-testid="pending">{pendingCount}</span>
      <span data-testid="queue-length">{queue.length}</span>
      <button data-testid="enqueue" onClick={() => enqueue({ url: '/test', method: 'POST', maxRetries: 3, label: 'Test' })}>
        Enqueue
      </button>
      <button data-testid="retry-all" onClick={() => retryAll()}>Retry All</button>
      <button data-testid="remove" onClick={() => { if (queue.length) remove(queue[0].id) }}>Remove</button>
      <button data-testid="clear" onClick={() => clear()}>Clear</button>
      {queue.map((a) => (
        <span key={a.id} data-testid="queue-item">{a.label}</span>
      ))}
    </div>
  )
}

describe('OfflineQueueContext', () => {
  beforeEach(() => {
    offlineQueue.clear()
    Object.defineProperty(navigator, 'onLine', { configurable: true, value: true })
  })

  afterEach(() => {
    offlineQueue.clear()
  })

  function renderProvider() {
    return render(
      <OfflineQueueProvider>
        <TestConsumer />
      </OfflineQueueProvider>,
    )
  }

  it('provides online status', () => {
    renderProvider()
    expect(screen.getByTestId('online')).toHaveTextContent('true')
  })

  it('shows online status when navigator.onLine changes', () => {
    renderProvider()
    act(() => {
      window.dispatchEvent(new Event('offline'))
    })
    expect(screen.getByTestId('online')).toHaveTextContent('false')

    act(() => {
      window.dispatchEvent(new Event('online'))
    })
    expect(screen.getByTestId('online')).toHaveTextContent('true')
  })

  it('enqueue adds to queue and updates pending count', async () => {
    const user = userEvent.setup()
    renderProvider()

    await user.click(screen.getByTestId('enqueue'))

    expect(screen.getByTestId('pending')).toHaveTextContent('1')
    expect(screen.getByTestId('queue-length')).toHaveTextContent('1')
    expect(screen.getAllByTestId('queue-item')).toHaveLength(1)
  })

  it('remove takes an item out of the queue', async () => {
    const user = userEvent.setup()
    renderProvider()

    await user.click(screen.getByTestId('enqueue'))
    expect(screen.getByTestId('pending')).toHaveTextContent('1')

    await user.click(screen.getByTestId('remove'))
    expect(screen.getByTestId('pending')).toHaveTextContent('0')
  })

  it('clear empties the queue', async () => {
    const user = userEvent.setup()
    renderProvider()

    await user.click(screen.getByTestId('enqueue'))
    await user.click(screen.getByTestId('enqueue'))
    expect(screen.getByTestId('pending')).toHaveTextContent('2')

    await user.click(screen.getByTestId('clear'))
    expect(screen.getByTestId('pending')).toHaveTextContent('0')
  })

  it('retryAll replays queue items', async () => {
    global.fetch = vi.fn().mockResolvedValue({ ok: true })
    const user = userEvent.setup()
    renderProvider()

    await user.click(screen.getByTestId('enqueue'))
    await user.click(screen.getByTestId('enqueue'))
    expect(screen.getByTestId('pending')).toHaveTextContent('2')

    await user.click(screen.getByTestId('retry-all'))
    expect(screen.getByTestId('pending')).toHaveTextContent('0')
  })

  it('throws error when used outside provider', () => {
    expect(() => render(<TestConsumer />)).toThrow(
      'useOfflineQueue must be used within OfflineQueueProvider',
    )
  })
})
