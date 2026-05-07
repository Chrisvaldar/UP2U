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
  const [error, setError] = useState("");
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

  function handleRankToggle(field: string, option: string) {
    const current = answers[field as keyof typeof answers] as string[];
    if (current.includes(option)) {
      const updated = current.filter((c) => c !== option);
      updateAnswer(field, updated);
    } else {
      updateAnswer(field, [...current, option]);
    }
  }

  function handleMultiToggle(field: string, option: string) {
    const current = answers[field as keyof typeof answers] as string[];
    if (current.includes(option)) {
      const updated = current.filter((c) => c !== option);
      updateAnswer(field, updated);
    } else {
      updateAnswer(field, [...current, option]);
    }
  }

  function updateAnswer(field: string, value: unknown) {
    setAnswers({ ...answers, [field]: value });
  }

  async function handleNext() {
    if (currentQuestion == QUESTIONS.length - 1) {
      try {
        await axios.post(`${API_BASE}/submit-answers/${code}`, {
          participant_name: state.name,
          answers: answers,
        });
        setSubmitted(true);
      } catch {
        setError("Failed to join. Check the code and try again.");
      }
    } else {
      setCurrentQuestion(currentQuestion + 1);
    }
  }

  if (submitted) {
    return <div>Waiting for everyone...</div>;
  }
  return (
    <div>
      {/* progress indicator */}
      {QUESTIONS[currentQuestion].type === "scale" &&
        //render scale input
        QUESTIONS[currentQuestion].options.map((option) => (
          <button
            key={option}
            onClick={() => updateAnswer(QUESTIONS[currentQuestion].id, option)}
          >
            {option}
          </button>
        ))}
      {QUESTIONS[currentQuestion].type === "single" &&
        // render single select chips
        QUESTIONS[currentQuestion].options.map((option) => (
          <button
            key={option}
            onClick={() => updateAnswer(QUESTIONS[currentQuestion].id, option)}
          >
            {option}
          </button>
        ))}
      {QUESTIONS[currentQuestion].type === "multi" &&
        // render multi chips
        QUESTIONS[currentQuestion].options.map((option) => (
          <button
            key={option}
            onClick={() =>
              handleMultiToggle(QUESTIONS[currentQuestion].id, option as string)
            }
          >
            {option}
          </button>
        ))}
      {QUESTIONS[currentQuestion].type === "rank" &&
        // render rank chips
        QUESTIONS[currentQuestion].options.map((option) => (
          <button
            key={option}
            onClick={() =>
              handleRankToggle(QUESTIONS[currentQuestion].id, option as string)
            }
          >
            {option}
          </button>
        ))}
      {/* next/submit button */}
      <button
        className="bg-primary text-primary-foreground rounded px-6 py-3 font-medium disabled:opacity-50"
        onClick={handleNext}
      >
        {currentQuestion == QUESTIONS.length - 1 ? "Submit" : "Next Question"}
      </button>
    </div>
  );
}
