/**
 * Error Boundary component to catch and handle React errors
 * Prevents entire app crash when a component fails
 */
import React from 'react';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null
    };
  }

  static getDerivedStateFromError(error) {
    // Update state so the next render will show the fallback UI
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    // Log the error to console for debugging
    console.error('Error Boundary caught an error:', error, errorInfo);

    this.setState({
      error,
      errorInfo
    });

    // You could also log to an error reporting service here
    // Example: logErrorToService(error, errorInfo);
  }

  handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null
    });
  };

  render() {
    if (this.state.hasError) {
      // Fallback UI
      return (
        <div
          className="min-h-screen bg-white text-black p-4 max-w-4xl mx-auto flex items-center justify-center"
          role="alert"
          aria-live="assertive"
        >
          <div className="border-2 border-red-600 p-8 rounded-lg max-w-2xl">
            <h1 className="text-2xl font-bold mb-4 text-red-600">
              Something went wrong
            </h1>

            <p className="text-gray-700 mb-4">
              The application encountered an unexpected error. Don't worry, your data is safe.
            </p>

            <div className="bg-gray-50 p-4 rounded mb-4 text-sm font-mono overflow-auto max-h-48">
              <div className="text-red-700 font-bold mb-2">
                {this.state.error && this.state.error.toString()}
              </div>
              {this.state.errorInfo && (
                <details className="text-gray-600">
                  <summary className="cursor-pointer hover:text-black">
                    Show error details
                  </summary>
                  <pre className="mt-2 whitespace-pre-wrap text-xs">
                    {this.state.errorInfo.componentStack}
                  </pre>
                </details>
              )}
            </div>

            <div className="flex gap-3">
              <button
                onClick={this.handleReset}
                className="px-4 py-2 bg-black text-white font-bold hover:bg-gray-800 transition-colors"
                aria-label="Try to recover from error"
              >
                TRY AGAIN
              </button>
              <button
                onClick={() => window.location.reload()}
                className="px-4 py-2 border-2 border-gray-300 font-bold hover:border-black transition-colors"
                aria-label="Reload the entire page"
              >
                RELOAD PAGE
              </button>
            </div>

            <p className="text-sm text-gray-500 mt-4 italic">
              If this problem persists, please contact support.
            </p>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
