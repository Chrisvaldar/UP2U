import { useState, useEffect } from "react";
import axios from "axios";
import { useNavigate, useParams, useLocation } from "react-router-dom";
import Button from "../components/Button";
import Input from "../components/Input";

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
          navigate(`/survey/${code}`, { state: { name } });
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
    <div className="flex flex-col items-center h-screen pt-12">
      <h1 className="text-3xl font-black text-green-800">Session Code:</h1>
      <h1 className="text-7xl font-black text-green-800 mb-4">{code}</h1>
      <h2 className="text-3xl font-black text-green-800 mb-12">
        {" "}
        Host: {host}
      </h2>
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
      {name === host && participants.length > 1 && (
        <div className="flex gap-4 mt-auto mb-8 items-center justify-center">
          <Input
            placeholder="Location"
            value={location}
            onChange={(e) => setLocation(e.target.value)}
          />
          <Button
            label="Start Session"
            onClick={handleStart}
            disabled={location.trim() === ""}
          />
        </div>
      )}{" "}
      {name !== host && (
        <div className="mt-auto mb-8">Waiting for host to start...</div>
      )}{" "}
    </div>
  );
}
