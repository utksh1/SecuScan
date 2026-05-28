import { useNavigate } from 'react-router-dom'

type Props = {
  errorMessage?: string
  onRetry: () => void
}

export default function ErrorFallback({
  errorMessage,
  onRetry,
}: Props) {
  const navigate = useNavigate()

  return (
    <div className="flex min-h-[60vh] items-center justify-center px-6 py-10">
      <div className="w-full max-w-lg rounded-2xl border border-gray-800 bg-zinc-900 p-8 shadow-xl">
        <div className="flex flex-col items-center text-center">
          <div className="mb-4 rounded-full bg-red-500/10 p-3">
            <span className="text-3xl">⚠️</span>
          </div>

          <h1 className="text-3xl font-bold tracking-tight text-white">
            Something went wrong
          </h1>

          <p className="mt-3 text-sm leading-6 text-gray-400">
            An unexpected frontend error occurred. You can retry the action
            or return to the dashboard.
          </p>

          {import.meta.env.DEV && errorMessage && (
            <pre className="mt-6 max-h-64 w-full overflow-auto rounded-lg border border-red-500/20 bg-black p-4 text-left text-sm text-red-400">
              {errorMessage}
            </pre>
          )}

          <div className="mt-8 flex flex-wrap justify-center gap-4">
            <button
              onClick={onRetry}
              className="rounded-lg bg-red-600 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-red-700"
            >
              Retry
            </button>

            <button
              onClick={() => navigate('/')}
              className="rounded-lg border border-gray-700 bg-zinc-800 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-zinc-700"
            >
              Go Home
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
