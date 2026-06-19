import { useState } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";

const API_BASE = "http://127.0.0.1:8000";

export default function HomePage() {
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [screen, setScreen] = useState("landing");
  const navigate = useNavigate();

  async function handleCreate() {
    const response = await axios.post(`${API_BASE}/create-session`, {
      host_name: name.trim()
    });

    const sessionCode = response.data.code;
    navigate(`/lobby/${sessionCode}`, { state: { name } });
  }
  async function handleJoin() {
    await axios.post(`${API_BASE}/join-session/${code}`, {
      participant_name: name.trim()
    });

    navigate(`/lobby/${code}`, { state: { name } });
  }

  return (
    <div>
      <h1 className="text-3xl font-black text-green-800">UP2U</h1>

      {screen === "landing" && (
        <div>
          <button className="font-semibold" onClick={() => setScreen("create")}>
            Create Session
          </button>
          <button className="font-semibold" onClick={() => setScreen("join")}>
            Join Session
          </button>
        </div>
      )}

      {screen === "create" && (
        <div>
          <input
            placeholder="your name"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
          <button onClick={handleCreate}>Create</button>
        </div>
      )}

      {screen === "join" && (
        <div>
          <input
            placeholder="your name"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
          <input
            placeholder="code"
            value={code}
            onChange={(e) => setCode(e.target.value)}
          />
          <button onClick={handleJoin}>Join</button>
        </div>
      )}
    </div>
  );
}
