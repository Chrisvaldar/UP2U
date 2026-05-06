import { useEffect, useRef, useState } from "react";
import { useParams, useLocation, useNavigate } from "react-router-dom";
import axios from "axios";

const API_BASE = "http://localhost:8000";
const WS_BASE = "ws://localhost:8000";

type LocationState = {
  name: string;
  isHost: boolean;
  location?: string;
};

export default function LobbyPage() {
  const { code } = useParams();
  const { state } = useLocation() as { state: LocationState };
  const navigate = useNavigate();

  const [participants, setParticipants] = useState<string[]>([]);
  const [starting, setStarting] = useState(false);

  // useRef stores the WebSocket instance without triggering re-renders.
  // If we used useState for this, updating the socket would cause a
  // re-render which could accidentally open duplicate connections.
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    // Step 1: fetch current session state so we show anyone already in the
    // lobby before we connected (e.g. host refreshed the page)
    axios.get(`${API_BASE}/session/${code}`).then((res) => {
      setParticipants(res.data.participants ?? []);
    });

    // Step 2: open WebSocket connection
    const ws = new WebSocket(`${WS_BASE}/ws/${code}/${state.name}`);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);

      if (message.type === "participant_joined") {
        // Backend sends the full updated participants list, so we just
        // replace state rather than trying to append and risk duplicates
        setParticipants(message.data.participants);
      }

      if (message.type === "session_started") {
        // Everyone navigates to survey when host starts the session
        navigate(`/survey/${code}`, {
          state: { name: state.name, isHost: state.isHost },
        });
      }
    };

    // Step 3: cleanup — close the WebSocket when leaving this page.
    // This runs when the component unmounts (navigating away, tab close).
    // Without this, the connection stays open forever.
    return () => {
      ws.close();
    };
  }, []); // empty array means this effect runs once on mount, never again

  async function handleStart() {
    setStarting(true);
    try {
      await axios.post(`${API_BASE}/start-session/${code}`, {
        host_name: state.name,
        location: state.location,
      });
      // No need to navigate here — the session_started WebSocket event
      // will fire back to us and trigger navigation for everyone including host
    } catch {
      setStarting(false);
    }
  }

  return (
    <div className="min-h-screen flex flex-col items-center justify-center gap-6 p-8">
      <h1 className="text-4xl font-bold">UP2U</h1>

      <div className="flex flex-col items-center gap-1">
        <p className="text-muted-foreground text-sm">Session code</p>
        <p className="text-3xl font-mono font-bold tracking-widest">{code}</p>
      </div>

      <div className="flex flex-col gap-3 w-full max-w-sm border rounded p-6">
        <h2 className="font-semibold">Participants ({participants.length})</h2>
        {participants.length === 0 ? (
          <p className="text-muted-foreground text-sm">
            Waiting for people to join...
          </p>
        ) : (
          <ul className="flex flex-col gap-2">
            {participants.map((p) => (
              <li key={p} className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-green-500" />
                <span>{p}</span>
                {p === state.name && (
                  <span className="text-xs text-muted-foreground">(you)</span>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>

      {state.isHost ? (
        <div className="flex flex-col items-center gap-2">
          <button
            className="bg-primary text-primary-foreground rounded px-6 py-3 font-medium disabled:opacity-50"
            onClick={handleStart}
            disabled={starting || participants.length < 1}
          >
            {starting ? "Starting..." : "Start session"}
          </button>
          <p className="text-xs text-muted-foreground">
            Everyone's in? Let's go.
          </p>
        </div>
      ) : (
        <p className="text-muted-foreground text-sm">
          Waiting for the host to start...
        </p>
      )}
    </div>
  );
}
