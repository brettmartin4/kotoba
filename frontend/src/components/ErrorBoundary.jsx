import { Component } from 'react'

// A class component is the only way to implement an error boundary in React.
// Without this, one uncaught render error blanks the entire app with no
// recovery path, which matters more for a local desktop-style app than a
// typical web page.
class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { error: null }
  }

  static getDerivedStateFromError(error) {
    return { error }
  }

  componentDidCatch(error, info) {
    console.error('KotobaForge crashed:', error, info)
  }

  render() {
    if (this.state.error) {
      return (
        <main className="dashboard">
          <h1>Something went wrong</h1>
          <p className="dashboard-error">{this.state.error.message}</p>
          <p>Please refresh the page. If this keeps happening, check the server console for details.</p>
        </main>
      )
    }
    return this.props.children
  }
}

export default ErrorBoundary
