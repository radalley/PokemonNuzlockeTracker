import { Component } from 'react'

class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = {
      hasError: false,
      error: null,
      stack: '',
    }
  }

  static getDerivedStateFromError(error) {
    return {
      hasError: true,
      error,
    }
  }

  componentDidCatch(error, info) {
    console.error('Frontend render error:', error, info)
    this.setState({
      stack: info?.componentStack || '',
    })
  }

  render() {
    if (!this.state.hasError) {
      return this.props.children
    }

    return (
      <div style={{ padding: '24px', color: '#f3f4f6', background: '#16171d', minHeight: '100vh' }}>
        <h1 style={{ marginTop: 0, fontSize: '1.2rem' }}>Frontend Render Error</h1>
        <div style={{ marginBottom: '12px', color: '#cbd5e1' }}>
          {this.state.error?.message || 'Unknown error'}
        </div>
        {this.state.stack ? (
          <pre style={{ whiteSpace: 'pre-wrap', background: '#0f1117', border: '1px solid #343a47', borderRadius: '8px', padding: '12px', overflowX: 'auto' }}>
            {this.state.stack}
          </pre>
        ) : null}
      </div>
    )
  }
}

export default ErrorBoundary