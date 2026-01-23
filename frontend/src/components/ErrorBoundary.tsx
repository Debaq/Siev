import { Component, ErrorInfo, ReactNode } from 'react'

interface Props {
  children?: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null
  }

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("Uncaught error:", error, errorInfo)
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div className="fixed inset-0 bg-red-900 text-white p-8 flex flex-col items-center justify-center z-[99999]">
          <h1 className="text-3xl font-bold mb-4">Algo salió mal</h1>
          <pre className="bg-black/50 p-4 rounded text-sm overflow-auto max-w-full">
            {this.state.error?.toString()}
          </pre>
          <button 
            className="mt-8 px-4 py-2 bg-white text-red-900 rounded font-bold"
            onClick={() => window.location.reload()}
          >
            Recargar Aplicación
          </button>
        </div>
      )
    }

    return this.props.children
  }
}

export default ErrorBoundary
