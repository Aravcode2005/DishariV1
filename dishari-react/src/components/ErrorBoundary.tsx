import { Component, type ErrorInfo, type ReactNode } from 'react';
import { AlertTriangle } from 'lucide-react';

interface Props { children: ReactNode }
interface State { hasError: boolean }
export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };
  static getDerivedStateFromError(): State { return { hasError: true }; }
  componentDidCatch(_error: Error, _info: ErrorInfo) {
    // Intentionally do not log case contents or PII to the console.
    console.error('A Dishari UI rendering error occurred.');
  }
  render() {
    if (!this.state.hasError) return this.props.children;
    return (
      <main className="container" style={{ paddingTop: 64 }}>
        <section className="panel error-boundary" role="alert">
          <AlertTriangle size={30} aria-hidden="true" />
          <h1>Something went wrong</h1>
          <p>The interface could not display this case. No automatic submission was made.</p>
          <button className="button button-primary" type="button" onClick={() => window.location.reload()}>Reload Dishari</button>
        </section>
      </main>
    );
  }
}
