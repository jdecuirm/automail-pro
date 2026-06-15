import { useState, useEffect } from "react";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

interface HealthResponse {
  status: string;
  service: string;
}

function App() {
  const [backendStatus, setBackendStatus] = useState<string | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    fetch(`${API_BASE}/health`)
      .then((res) => res.json() as Promise<HealthResponse>)
      .then((data) => setBackendStatus(data.status))
      .catch(() => setError(true));
  }, []);

  return (
    <main className="min-h-screen bg-gray-950 text-white flex flex-col items-center justify-center gap-4">
      <h1 className="text-4xl font-bold tracking-tight">AutoMail Pro</h1>
      <p className="text-lg text-gray-400">
        Backend status:{" "}
        {error ? (
          <span className="text-red-400 font-medium">Backend unreachable</span>
        ) : backendStatus === null ? (
          <span className="text-yellow-400 font-medium">checking…</span>
        ) : (
          <span className="text-green-400 font-medium">{backendStatus}</span>
        )}
      </p>
    </main>
  );
}

export default App;
