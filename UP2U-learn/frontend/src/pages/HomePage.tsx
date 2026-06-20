import { useState } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";
import Button from "../components/Button";
import Input from "../components/Input";

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
          <Button label="Create Session" onClick={() => setScreen("create")} />
          <Button label="Join Session" onClick={() => setScreen("join")} />
        </div>
      )}

      {screen === "create" && (
        <div className="flex flex-col">
          <Input
            placeholder="Name"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
          <Button label="Create" onClick={handleCreate} />
        </div>
      )}

      {screen === "join" && (
        <div className="flex flex-col">
          <Input
            placeholder="Name"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
          <Input
            placeholder="Session Code"
            value={code}
            onChange={(e) => setCode(e.target.value)}
          />
          <Button label="Join" onClick={handleJoin} />
        </div>
      )}
    </div>
  );
}
