import { useState, useEffect } from "react";
import axios from "axios";
import { useNavigate, useParams, useLocation } from "react-router-dom";
import Button from "../components/Button";
import Input from "../components/Input";
import { Slider } from "@/components/ui/slider";
import SortableItem from "@/components/SortableItem";
import { DragDropProvider } from "@dnd-kit/react";
import { move } from "@dnd-kit/helpers";

const API_BASE = "http://127.0.0.1:8000";

export default function Survey() {
  const { code } = useParams();
  const name = useLocation().state?.name;
  const [submitted, setSubmitted] = useState<string[]>([]);
  const [total, setTotal] = useState(0);
  const [hunger, setHunger] = useState(1);
  const [vibe, setVibe] = useState("");
  const [cuisinesRanked, setCuisinesRanked] = useState<string[]>([
    "Chinese",
    "Italian",
    "Korean",
    "Indonesian",
    "Thai"
  ]);
  const [travelDistance, setTravelDistance] = useState("");
  const [dietary, setDietary] = useState<string[]>([]);
  const [step, setStep] = useState(0);
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
      const session = await axios.get(`${API_BASE}/session/${code}`);
      setTotal(session.data.participants.length);
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
    <div className="flex flex-col items-center justify-center h-screen">
      {step === 0 && (
        <div className="flex flex-col items-center gap-6">
          <h2 className="text-3xl font-black text-green-800 mb-4">
            How hungry are you right now? (1-5)
          </h2>
          <div className="bg-green-100 text-green-800 text-center px-4 py-2 text-xl rounded-full">
            {hunger}
          </div>
          <Slider
            min={1}
            max={5}
            step={1}
            value={[hunger]}
            onValueChange={(val) => setHunger(val[0])}
          />
          <Button label="Next" onClick={() => setStep(step + 1)} />
        </div>
      )}
      {step === 1 && (
        <div className="flex flex-col items-center gap-6">
          <h2 className="text-3xl font-black text-green-800 mb-4">
            What's the vibe you're looking for?
          </h2>
          <div className="flex flex-row gap-4">
            <Button
              variant={vibe === "Quick and ez" ? "solid" : "outline"}
              label="Quick and ez"
              onClick={() => setVibe("Quick and ez")}
            />
            <Button
              variant={vibe === "Casual" ? "solid" : "outline"}
              label="Casual"
              onClick={() => setVibe("Casual")}
            />
            <Button
              variant={vibe === "Nice place" ? "solid" : "outline"}
              label="Nice place"
              onClick={() => setVibe("Nice place")}
            />
          </div>
          {vibe !== "" && (
            <Button label="Next" onClick={() => setStep(step + 1)} />
          )}
        </div>
      )}
      {step === 2 && (
        <div className="flex flex-col items-center gap-6">
          <h2 className="text-3xl font-black text-green-800 mb-4">
            What kind of food are you feeling right now?
          </h2>
          <DragDropProvider
            onDragOver={(event) => {
              setCuisinesRanked((prev) => move(prev, event));
            }}
          >
            <div className="flex flex-col">
              {cuisinesRanked.map((p, index) => (
                <SortableItem id={p} index={index} key={p} />
              ))}
            </div>
          </DragDropProvider>

          <Button label="Next" onClick={() => setStep(step + 1)} />
        </div>
      )}
      {step === 3 && (
        <div className="flex flex-col items-center gap-6">
          <h2 className="text-3xl font-black text-green-800 mb-4">
            What kind of travel are we comfortable with?
          </h2>
          <div className="flex flex-row gap-4">
            <Button
              variant={
                travelDistance === "Short walk (<500m)" ? "solid" : "outline"
              }
              label="Short walk (<500m)"
              onClick={() => setTravelDistance("Short walk (<500m)")}
            />
            <Button
              variant={
                travelDistance === "Public transport (<2km)"
                  ? "solid"
                  : "outline"
              }
              label="Public transport (<2km)"
              onClick={() => setTravelDistance("Public transport (<2km)")}
            />
            <Button
              variant={travelDistance === "Don't mind" ? "solid" : "outline"}
              label="Don't mind"
              onClick={() => setTravelDistance("Ddon't mind")}
            />
          </div>
          {travelDistance !== "" && (
            <Button label="Next" onClick={() => setStep(step + 1)} />
          )}
        </div>
      )}
      {step === 4 && (
        <div className="flex flex-col items-center gap-6">
          <h2 className="text-3xl font-black text-green-800 mb-4">
            Any dietary requirements? (Multi-select)
          </h2>
          <div className="flex flex-row gap-4">
            {["Vegetarian", "Vegan", "Gluten-free", "Halal", "Kosher"].map(
              (p) => (
                <Button
                  key={p}
                  label={p}
                  variant={dietary.includes(p) ? "solid" : "outline"}
                  onClick={() => {
                    if (!dietary.includes(p)) {
                      setDietary([...dietary, p]);
                    } else {
                      setDietary(dietary.filter((item) => item !== p));
                    }
                  }}
                />
              )
            )}
          </div>
          <Button label="Submit" onClick={handleSubmit} />
          <h3>
            Submitted: {submitted.length}/{total}
          </h3>
        </div>
      )}
      {submitted.length > 0 && (
        <h3>
          Submitted: {submitted.length}/{total}
        </h3>
      )}
    </div>
  );
}
