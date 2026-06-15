import { useState, useEffect } from "react";
import axios from "axios";
import { useNavigate, useParams, useLocation } from "react-router-dom";

const API_BASE = "http://127.0.0.1:8000";
export default function Lobby() {
  const { code } = useParams();
  const name = useLocation().state?.name;
  const [host, setHost] = useState("");
  const [participants, setParticipants] = useState([]);
  const [location, setLocation] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    async function get_session() {
      const ws = new WebSocket(`ws://127.0.0.1:8000/ws/${code}/${name}`);
      const session = await axios.get(`${API_BASE}/session/${code}`);
      const host = session["data"]["host"];
      setHost(host);
      const participants = session["data"]["participants"];
      setParticipants(participants);

      ws.onmessage = (event) => {
        const message = JSON.parse(event.data);
        if (message["type"] == "participant_joined") {
          setParticipants(message["data"]["participants"]);
        } else if (message["type"] == "session_started") {
          navigate(`/survey/${code}`);
        }
      };
    }
    get_session();
  }, []);

  async function handleStart() {
    await axios.post(`${API_BASE}/start-session/${code}`, {
      host_name: name.trim(),
      location: location
    });
  }

  return (
    <div>
      <h1>{code}</h1>
      <h2>Host: {host}</h2>
      <ul>
        {participants.map((p) => (
          <li key={p}> {p}</li>
        ))}
      </ul>
      {name === host && participants.length > 1 && (
        <div>
          <input
            placeholder="Location"
            value={location}
            onChange={(e) => setLocation(e.target.value)}
          />
          <button onClick={handleStart} disabled={location.trim() === ""}>
            Start Session
          </button>
        </div>
      )}{" "}
    </div>
  );
}
