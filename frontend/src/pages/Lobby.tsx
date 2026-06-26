import { useState, useEffect } from "react";
import axios from "axios";
import { useNavigate, useParams, useLocation } from "react-router-dom";
import Button from "../components/Button";
import { LocationAutocomplete } from "../components/LocationAutocomplete";
import { API_BASE, WS_BASE } from "@/lib/config";
export default function Lobby() {
  const { code } = useParams();
  const name = useLocation().state?.name ?? "";
  const [host, setHost] = useState("");
  const [participants, setParticipants] = useState<string[]>([]);
  const [lat, setLat] = useState<number | null>(null);
  const [lng, setLng] = useState<number | null>(null);
  const [dots, setDots] = useState("");
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    let cancelled = false;
    let ws: WebSocket | undefined;

    async function get_session() {
      if (!code || !name) {
        setError("Missing session details. Go back and join again.");
        return;
      }

      try {
        const session = await axios.get(`${API_BASE}/session/${code}`);
        if (cancelled) return;
        if (session.data?.error) {
          setError("Session not found. Check the code and try again.");
          return;
        }

        setHost(session.data.host);
        setParticipants(session.data.participants ?? []);

        ws = new WebSocket(`${WS_BASE}/ws/${code}/${name}`);

        ws.onmessage = (event) => {
          const message = JSON.parse(event.data);
          if (message["type"] == "participant_joined") {
            setParticipants(message["data"]["participants"]);
          } else if (message["type"] == "session_started") {
            navigate(`/survey/${code}`, { state: { name } });
          }
        };
        ws.onerror = () => {
          setError("Lost the live lobby connection. Refresh to reconnect.");
        };
      } catch {
        if (!cancelled) {
          setError("Could not load the session. Check that the backend is running.");
        }
      }
    }
    get_session();
    // Close the socket on page exit so remounts do not leave duplicate listeners.
    return () => {
      cancelled = true;
      ws?.close();
    };
  }, [code, name, navigate]);

  useEffect(() => {
    const interval = setInterval(() => {
      // Functional state keeps the interval independent of stale render values.
      setDots((prev) => (prev.length === 3 ? "." : prev + "."));
    }, 750);
    return () => clearInterval(interval);
  }, []);

  async function handleStart() {
    if (lat === null || lng === null) {
      setError("Choose a location before starting.");
      return;
    }

    setStarting(true);
    setError("");
    try {
      const response = await axios.post(`${API_BASE}/start-session/${code}`, {
        host_name: name.trim(),
        lat,
        lng
      });
      if (response.data?.error) {
        setError(response.data.error);
        setStarting(false);
      }
    } catch {
      setError("Could not start the session. Try again.");
      setStarting(false);
    }
  }

  return (
    <div className="flex flex-col items-center h-screen pt-12">
      <h1 className="text-3xl font-black text-green-800">Session Code:</h1>
      <h1 className="text-7xl font-black text-green-800 mb-4">{code}</h1>
      <h2 className="text-3xl font-black text-green-800 mb-12">
        {" "}
        Host: {host}
      </h2>
      {name === host && participants.length > 1 && (
        <div className="flex gap-4 mb-12 items-center justify-center">
          <LocationAutocomplete
            onPlaceSelect={(place) => {
              if (place?.location) {
                setLat(place.location.lat());
                setLng(place.location.lng());
              }
            }}
          />
          <Button
            label={starting ? "Starting..." : "Start Session"}
            onClick={handleStart}
            disabled={starting || lat === null || lng === null}
          />
        </div>
      )}{" "}
      {error && <p className="text-red-600 text-sm mb-8">{error}</p>}
      <div className="grid grid-cols-3 gap-4">
        {participants.map((p) => (
          <div
            className="bg-green-100 text-green-800 text-center px-4 py-2 mb-8 text-xl rounded-full"
            key={p}
          >
            {" "}
            {p}
          </div>
        ))}
      </div>
      {name !== host && (
        <div className="mt-auto mb-8">{`Waiting for host to start${dots}`}</div>
      )}{" "}
    </div>
  );
}
