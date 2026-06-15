import { useState, useEffect } from "react";
import axios from "axios";
import { useNavigate, useParams, useLocation } from "react-router-dom";

const API_BASE = "http://127.0.0.1:8000";

export default function Survey() {
  const { code } = useParams();
  const name = useLocation().state?.name;
  const [submitted, setSubmitted] = useState([]);
  const [total, setTotal] = useState(0);
  const [hunger, setHunger] = useState(3);
  const [vibe, setVibe] = useState("");
  const [cuisinesRanked, setCuisinesRanked] = useState([]);
  const [travelDistance, setTravelDistance] = useState("");
  const [dietary, setDietary] = useState([]);
  const navigate = useNavigate();

  useEffect(() => {
    async function load_survey() {
      const ws = new WebSocket(`ws://127.0.0.1:8000/ws/${code}/${name}`);
      ws.onmessage = (event) => {
        const message = JSON.parse(event.data);
        if (message["type"] == "answer_submitted") {
          setSubmitted(message["data"]["submitted"]);
          setTotal(message["data"]["total"]);
        } else if (message["type"] == "reveal_ready") {
          navigate(`/reveal/${code}`, {
            state: { name, reveal: message.data }
          });
        }
      };
    }
    load_survey();
  }, []);

  return (
    <div>
      <h1>Survey</h1>

      <h2>Hunger</h2>
      <input
        type="range"
        min="1"
        max="5"
        step="1"
        value={hunger}
        onChange={(e) => setHunger(Number(e.target.value))}
      />

      <h2>Vibe</h2>
      <button onClick={() => setVibe("quick and ez")}>quick and ez</button>
      <button onClick={() => setVibe("casual")}>casual</button>
      <button onClick={() => setVibe("nice place")}>nice place</button>
    </div>
  );
}
