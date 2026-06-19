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
    <div className="flex justify-center items-center h-screen flex-col">
      <h1 className="text-8xl font-black text-green-800 mb-8">UP2U</h1>

      {screen === "landing" && (
        <div className="flex flex-col gap-4 text-xl">
          <button
            className="font-semibold bg-green-700 text-white px-6 py-3 rounded-full"
            onClick={() => setScreen("create")}
          >
            Create Session
          </button>
          <button
            className="font-semibold bg-green-700 text-white px-6 py-3 rounded-full"
            onClick={() => setScreen("join")}
          >
            Join Session
          </button>
        </div>
      )}

      {screen === "create" && (
        <div className="flex flex-col">
          <input
            placeholder="your name"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
          <button
            className="font-semibold bg-green-700 text-white px-1 py-1 rounded-full"
            onClick={handleCreate}
          >
            Create
          </button>
        </div>
      )}

      {screen === "join" && (
        <div className="flex flex-col">
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
