import { useState } from "react";
import axios from "axios"
import { useNavigate } from "react-router-dom"; 


const API_BASE = "http://localhost:8000";

export default function HomePage() {
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const navigate = useNavigate();

  async function handleCreate(){
    const response = await axios.post(`${API_BASE}/create-session`, {hostname: name.trim()})
    
    const sessionCode = response.data.code
    navigate(`/lobby/${sessionCode}`)
  }

  return (
    <div>
      <h1>UP2U</h1>

      <input
        placeholder="your name"
        value={name}
        onChange={(e) => setName(e.target.value)}
      />
      <button>Create Session</button>

      <input
        placeholder="code"
        value={code}
        onChange={(e) => setCode(e.target.value)}
      />
      <button>Join Session</button>
    </div>
  );
}
