import React from 'react'

type ErrorBoundaryProps = {
    children: React.ReactNode
}

type ErrorBoundaryState = {
    hasError: boolean
    error?: Error
}

export default class ErrorBoundary extends React.Component<
    ErrorBoundaryProps,
    ErrorBoundaryState
> {
    state: ErrorBoundaryState = {
        hasError: false,
    }

    static getDerivedStateFromError(error: Error): ErrorBoundaryState {
        return {
            hasError: true,
            error,
        }
    }

    componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
        console.error('Unhandled frontend error:', error, errorInfo)
    }

    handleReload = () => {
        window.location.reload()
    }

    handleReset = () => {
        this.setState({ hasError: false, error: undefined })
    }

    render() {
        if (this.state.hasError) {
            return (
                <main
                    role="alert"
                    aria-labelledby="error-boundary-title"
                    style={{
                        minHeight: '100vh',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        padding: '2rem',
                        background: 'var(--bg-primary)',
                        color: 'var(--text-primary)',
                    }}
                >
                    <section
                        style={{
                            maxWidth: '620px',
                            width: '100%',
                            padding: '2rem',
                            border: '1px solid rgba(192, 192, 200, 0.18)',
                            borderRadius: '18px',
                            background:
                                'linear-gradient(145deg, var(--bg-secondary), var(--bg-primary))',
                            boxShadow: '0 24px 80px rgba(0, 0, 0, 0.35)',
                        }}
                    >
                        <p
                            style={{
                                color: 'var(--rag-amber)',
                                fontFamily: 'var(--font-mono)',
                                fontSize: '0.8rem',
                                marginBottom: '0.75rem',
                                textTransform: 'uppercase',
                                letterSpacing: '0.08em',
                            }}
                        >
                            Frontend exception caught
                        </p>

                        <h1 id="error-boundary-title" style={{ marginBottom: '0.75rem' }}>
                            Something went wrong
                        </h1>

                        <p style={{ marginBottom: '1.5rem', lineHeight: 1.6 }}>
                            SecuScan recovered from an unexpected interface error. You can try
                            returning to the app or reload the page.
                        </p>

                        {this.state.error?.message ? (
                            <pre
                                style={{
                                    whiteSpace: 'pre-wrap',
                                    wordBreak: 'break-word',
                                    marginBottom: '1.5rem',
                                    padding: '1rem',
                                    borderRadius: '12px',
                                    background: 'rgba(255, 255, 255, 0.04)',
                                    color: 'var(--text-secondary)',
                                    fontFamily: 'var(--font-mono)',
                                    fontSize: '0.85rem',
                                }}
                            >
                                {this.state.error.message}
                            </pre>
                        ) : null}

                        <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
                            <button
                                type="button"
                                onClick={this.handleReset}
                                style={{
                                    padding: '0.75rem 1rem',
                                    borderRadius: '10px',
                                    border: '1px solid rgba(192, 192, 200, 0.25)',
                                    background: 'var(--bg-elevated)',
                                    color: 'var(--text-primary)',
                                    cursor: 'pointer',
                                }}
                            >
                                Return to app
                            </button>

                            <button
                                type="button"
                                onClick={this.handleReload}
                                style={{
                                    padding: '0.75rem 1rem',
                                    borderRadius: '10px',
                                    border: '1px solid rgba(192, 192, 200, 0.25)',
                                    background: 'transparent',
                                    color: 'var(--text-secondary)',
                                    cursor: 'pointer',
                                }}
                            >
                                Reload page
                            </button>
                        </div>
                    </section>
                </main>
            )
        }

        return this.props.children
    }
}
