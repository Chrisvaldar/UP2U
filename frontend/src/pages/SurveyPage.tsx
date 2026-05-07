import { useEffect, useRef, useState } from "react";
import { useParams, useLocation, useNavigate } from "react-router-dom";
import axios from "axios";

const API_BASE = "http://localhost:8000";
const WS_BASE = "ws://localhost:8000";

// Question bank to display to user (cuisines subject to change)
const QUESTIONS = [
  { id: "hunger", type: "scale", options: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10] },
  {
    id: "vibe",
    type: "single",
    options: ["fancy", "anything", "casual", "quick"],
  },
  {
    id: "cuisines_ranked",
    type: "rank",
    options: [
      "chinese",
      "japanese",
      "indian",
      "korean",
      "malaysian",
      "vietnamese",
      "thai",
      "greek",
      "indonesian",
      "turkish",
    ],
  },
  {
    id: "travel_distance",
    type: "single",
    options: ["short walk (<500m)", "public transport (<2km)", "don't mind"],
  },
  {
    id: "dietary",
    type: "multi",
    options: ["vegetarian", "vegan", "halal", "gluten-free", "kosher"],
  },
];

type LocationState = {
  name: string;
  isHost: boolean;
  location?: string;
};

export default function SurveyPage() {
  const { code } = useParams();
  const { state } = useLocation() as { state: LocationState };
  const navigate = useNavigate();
  const [currentQuestion, setCurrentQuestion] = useState(0);
  const [answers, setAnswers] = useState({
    hunger: 0,
    vibe: "",
    cuisines_ranked: [] as string[],
    travel_distance: "",
    dietary: [] as string[],
  });
  const [submitted, setSubmitted] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    // Connect WebSocket and check reveal_ready event
    const ws = new WebSocket(`${WS_BASE}/ws/${code}/${state.name}`);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      if (message.type === "reveal_ready") {
        navigate(`/reveal/${code}`, {
          state: { name: state.name, isHost: state.isHost },
        });
      }
    };

    return () => {
      ws.close();
    };
  }, []);

  function handleCuisineToggle(cuisine: string) {
    const current = answers.cuisines_ranked;
    if (current.includes(cuisine)) {
      const updated = current.filter((c) => c !== cuisine);
      updateAnswer("cuisines_ranked", updated);
    } else {
      updateAnswer("cuisines_ranked", [...current, cuisine]);
    }
  }

  function updateAnswer(field: string, value: unknown) {
    setAnswers({ ...answers, [field]: value });
  }

  async function handleNext() {
    if (currentQuestion == QUESTIONS.length - 1) {
      await axios.post(`${API_BASE}/submit-answers/${code}`, {
        participant_name: state.name,
        answers: answers,
      });
      setSubmitted(true);
    } else {
      setCurrentQuestion(currentQuestion + 1);
    }
  }
}
