import { useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";

const API_BASE = "http://localhost:8000";

type Mode = "none" | "create" | "join";

export default function HomePage() {
  const navigate = useNavigate();
  const [mode, setMode] = useState<Mode>("none");
  const [name, setName] = useState("");
  const [joinCode, setJoinCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  function selectMode(selected: Mode) {
    // If clicking the already-open mode, close it
    setMode(mode === selected ? "none" : selected);
    setError("");
    setName("");
    setJoinCode("");
  }

  async function handleCreate() {
    if (!name.trim()) return setError("Enter your name");
    setLoading(true);
    setError("");
    try {
      const res = await axios.post(`${API_BASE}/create-session`, {
        host_name: name.trim(),
      });
      const code = res.data.session_code;
      await axios.post(`${API_BASE}/join-session/${code}`, {
        participant_name: name.trim(),
      });
      navigate(`/lobby/${code}`, {
        state: { name: name.trim(), isHost: true },
      });
    } catch {
      setError("Failed to create session. Is the backend running?");
    } finally {
      setLoading(false);
    }
  }

  async function handleJoin() {
    if (!name.trim()) return setError("Enter your name");
    if (!joinCode.trim()) return setError("Enter a session code");
    setLoading(true);
    setError("");
    try {
      await axios.post(
        `${API_BASE}/join-session/${joinCode.trim().toUpperCase()}`,
        {
          participant_name: name.trim(),
        },
      );
      navigate(`/lobby/${joinCode.trim().toUpperCase()}`, {
        state: { name: name.trim(), isHost: false },
      });
    } catch {
      setError("Failed to join. Check the code and try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex flex-col items-center justify-center gap-6 p-8">
      <h1 className="text-4xl font-bold">UP2U</h1>
      <p className="text-muted-foreground">
        Figure out where to eat, together.
      </p>

      <div className="flex gap-4">
        <button
          className="border rounded px-6 py-3 font-medium hover:bg-muted transition-colors"
          onClick={() => selectMode("create")}
        >
          Create session
        </button>
        <button
          className="border rounded px-6 py-3 font-medium hover:bg-muted transition-colors"
          onClick={() => selectMode("join")}
        >
          Join session
        </button>
      </div>

      {/* Inline form — only renders when a mode is selected */}
      {mode !== "none" && (
        <div className="flex flex-col gap-3 w-full max-w-sm border rounded p-6">
          <h2 className="font-semibold">
            {mode === "create" ? "Create a session" : "Join a session"}
          </h2>

          <input
            className="border rounded px-3 py-2"
            placeholder="Your name"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />

          {mode === "join" && (
            <input
              className="border rounded px-3 py-2 uppercase"
              placeholder="Session code"
              value={joinCode}
              onChange={(e) => setJoinCode(e.target.value)}
              maxLength={6}
            />
          )}

          {error && <p className="text-destructive text-sm">{error}</p>}

          <button
            className="bg-primary text-primary-foreground rounded px-4 py-2 font-medium disabled:opacity-50"
            onClick={mode === "create" ? handleCreate : handleJoin}
            disabled={loading}
          >
            {loading ? "..." : mode === "create" ? "Create" : "Join"}
          </button>
        </div>
      )}
    </div>
  );
}
