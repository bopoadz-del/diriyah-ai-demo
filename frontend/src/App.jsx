import "./App.css";

function App() {
  return (
    <div className="app">
      <header className="app__header">
        <h1 className="app__title">Diriyah AI Demo</h1>
        <p className="app__subtitle">Stub administrative console</p>
      </header>

      <main className="app__content">
        <section className="app__panel">
          <h2>Deployment ready UI</h2>
          <p>
            The production Docker image now ships with the compiled frontend bundle so
            the FastAPI backend can serve the single-page app directly. Use the
            buttons below to verify the health of the stack or rebuild the bundle
            when iterating locally.
          </p>
          <div className="app__actions">
            <a className="app__link" href="/health">
              Backend health check
            </a>
            <a className="app__link" href="https://render.com/docs" target="_blank" rel="noreferrer">
              Render documentation
            </a>
          </div>
        </section>

        <section className="app__panel">
          <h2>Getting started</h2>
          <ol>
            <li>Run <code>npm run dev</code> inside the <code>frontend</code> folder for hot reloads.</li>
            <li>Execute <code>npm run build</code> before pushing to confirm the static bundle.</li>
            <li>Start the API with <code>uvicorn backend.main:app --reload</code> to develop end-to-end.</li>
          </ol>
        </section>
      </main>
    </div>
  );
}

export default App;
