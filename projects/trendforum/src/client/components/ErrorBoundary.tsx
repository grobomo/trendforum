import { Component, type ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback;
      return (
        <div className="bg-card border border-red-900/50 rounded-md p-6 text-center">
          <h2 className="text-accent font-bold text-lg mb-2">Something went wrong</h2>
          <p className="text-muted text-sm mb-4">
            {this.state.error?.message || 'An unexpected error occurred'}
          </p>
          <button
            onClick={() => this.setState({ hasError: false, error: null })}
            className="px-4 py-1.5 bg-accent text-white rounded text-sm hover:bg-accent-hover transition"
          >
            Try Again
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
