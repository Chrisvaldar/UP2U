import { useState, useEffect } from "react";
import axios from "axios";
import { useNavigate, useParams, useLocation } from "react-router-dom";

const API_BASE = "http://127.0.0.1:8000";

export default function Survey() {
  const { code } = useParams();
  const name = useLocation().state?.name;
  const [submitted, setSubmitted] = useState<string[]>([]);
  const [total, setTotal] = useState(0);
  const [hunger, setHunger] = useState(3);
  const [vibe, setVibe] = useState("");
  const [cuisinesRanked, setCuisinesRanked] = useState<string[]>([]);
  const [travelDistance, setTravelDistance] = useState("");
  const [dietary, setDietary] = useState<string[]>([]);
  const navigate = useNavigate();

  async function handleSubmit() {
    await axios.post(`${API_BASE}/submit-answers/${code}`, {
      participant_name: name.trim(),
      answers: {
        "hunger": hunger,
        "vibe": vibe,
        "cuisines_ranked": cuisinesRanked,
        "travel_distance": travelDistance,
        "dietary": dietary
      }
    });
  }

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

      <h2>Cuisine</h2>

      <div>
        {["Chinese", "Italian", "Korean", "Indonesian", "Thai"]
          .filter((p) => !cuisinesRanked.includes(p))
          .map((p) => (
            <button
              key={p}
              onClick={() => {
                if (!cuisinesRanked.includes(p)) {
                  setCuisinesRanked([...cuisinesRanked, p]);
                }
              }}
            >
              {p}
            </button>
          ))}
      </div>

      <ol>
        {cuisinesRanked.map((p) => (
          <li key={p}> {p}</li>
        ))}
      </ol>

      <h2>Travel Distance</h2>
      <button onClick={() => setTravelDistance("short walk (<500m)")}>
        short walk (&lt;500m)
      </button>
      <button onClick={() => setTravelDistance("public transport (<2km)")}>
        public transport (&lt;2km)
      </button>
      <button onClick={() => setTravelDistance("don't mind")}>
        don't mind
      </button>

      <h2>Dietary</h2>
      <div>
        {["vegetarian", "vegan", "gluten-free", "halal", "kosher"].map((p) => (
          <button
            key={p}
            onClick={() => {
              if (!dietary.includes(p)) {
                setDietary([...dietary, p]);
              } else {
                setDietary(dietary.filter((item) => item !== p));
              }
            }}
          >
            {p}
          </button>
        ))}
      </div>

      <ul>
        {dietary.map((p) => (
          <li key={p}> {p}</li>
        ))}
      </ul>
    </div>
  );
}
