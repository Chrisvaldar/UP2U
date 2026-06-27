import { useState, useEffect } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";
import Button from "../components/Button";
import Input from "../components/Input";
import ErrorMessage from "../components/ErrorMessage";
import { API_BASE } from "@/lib/config";
import { saveParticipantName } from "@/lib/session";
type Screen = "landing" | "create" | "join";

export default function HomePage() {
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [screen, setScreen] = useState<Screen>("landing");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    const message = sessionStorage.getItem("up2u:message");
    if (message) {
      setError(message);
      sessionStorage.removeItem("up2u:message");
    }
  }, []);
  async function handleCreate() {
    const trimmedName = name.trim();
    if (!trimmedName) {
      setError("Enter your name first.");
      return;
    }

    setLoading(true);
    setError("");
    try {
      const response = await axios.post(`${API_BASE}/create-session`, {
        host_name: trimmedName,
      });
      const sessionCode = response.data.code;
      saveParticipantName(sessionCode, trimmedName);
      navigate(`/lobby/${sessionCode}`, { state: { name: trimmedName } });
    } catch {
      setError(
        "Could not create a session. Check that the backend is running.",
      );
    } finally {
      setLoading(false);
    }
  }

  async function handleJoin() {
    const trimmedName = name.trim();
    const sessionCode = code.trim().toUpperCase();
    if (!trimmedName) {
      setError("Enter your name first.");
      return;
    }
    if (!sessionCode) {
      setError("Enter a session code.");
      return;
    }

    setLoading(true);
    setError("");
    try {
      const response = await axios.post(
        `${API_BASE}/join-session/${sessionCode}`,
        {
          participant_name: trimmedName,
        },
      );
      if (response.data?.error) {
        setError(response.data.error);
        return;
      }
      saveParticipantName(sessionCode, trimmedName);
      if (response.data.status === "active") {
        navigate(`/survey/${sessionCode}`, { state: { name: trimmedName } });
      } else {
        navigate(`/lobby/${sessionCode}`, { state: { name: trimmedName } });
      }
    } catch {
      setError("Could not join that session. Check the code and try again.");
    } finally {
      setLoading(false);
    }
  }

  function selectScreen(nextScreen: Screen) {
    setScreen(nextScreen);
    setError("");
  }

  return (
    <div className="flex justify-center items-center h-screen flex-col">
      <h1 className="text-8xl font-black text-green-800 mb-8">UP2U</h1>

      {screen === "landing" && (
        <div className="flex flex-col gap-4 text-xl">
          <Button
            label="Create Session"
            onClick={() => selectScreen("create")}
          />
          <Button label="Join Session" onClick={() => selectScreen("join")} />
          <ErrorMessage message={error} />
        </div>
      )}

      {screen === "create" && (
        <div className="flex flex-col gap-4">
          <Input
            placeholder="Name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            disabled={loading}
          />
          <ErrorMessage message={error} />
          <Button
            label={loading ? "Creating..." : "Create"}
            onClick={handleCreate}
            disabled={loading}
          />
        </div>
      )}

      {screen === "join" && (
        <div className="flex flex-col gap-4">
          <Input
            placeholder="Name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            disabled={loading}
          />
          <Input
            placeholder="Session Code"
            value={code}
            onChange={(e) => setCode(e.target.value.toUpperCase())}
            maxLength={6}
            disabled={loading}
          />
          <ErrorMessage message={error} />
          <Button
            label={loading ? "Joining..." : "Join"}
            onClick={handleJoin}
            disabled={loading}
          />
        </div>
      )}
    </div>
  );
}
