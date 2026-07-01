import { useState, useEffect } from "react";
import { useNavigate, useParams, useLocation } from "react-router-dom";
import useEmblaCarousel from "embla-carousel-react";
import Button from "../components/Button";
import RestaurantCard from "../components/RestaurantCard";
import {
  getParticipantName,
  getReveal,
  clearReveal,
  setFlashMessage,
} from "@/lib/session";
import ErrorMessage from "../components/ErrorMessage";
import { API_BASE, WS_BASE } from "@/lib/config";
import axios from "axios";

export default function Reveal() {
  const { code } = useParams();
  const navigate = useNavigate();
  const reveal = code ? getReveal(code) : undefined;
  const [step, setStep] = useState(0);
  const name =
    useLocation().state?.name ?? getParticipantName(code ?? "") ?? "";
  const [host, setHost] = useState("");
  const [error, setError] = useState("");
  const [emblaRef, emblaApi] = useEmblaCarousel({ loop: true });

  useEffect(() => {
    if (reveal && import.meta.env.DEV) {
      console.log("[UP2U] reveal (display)", reveal);
    }
  }, [reveal]);

  useEffect(() => {
    let cancelled = false;
    let ws: WebSocket | undefined;

    async function start_reveal() {
      if (!code || !name) {
        return;
      }

      try {
        const session = await axios.get(`${API_BASE}/session/${code}`);
        if (cancelled) return;
        setHost(session.data.host);
        ws = new WebSocket(`${WS_BASE}/ws/${code}/${name}`);
        ws.onmessage = (event) => {
          const message = JSON.parse(event.data);
          if (message["type"] === "session_ended") {
            clearReveal(code.trim().toUpperCase());
            setFlashMessage("Session ended");
            navigate("/");
          }
        };
      } catch (err) {
        if (axios.isAxiosError(err) && err.response) {
          setFlashMessage("Page not found");
        } else {
          setFlashMessage("Network failed");
        }
        navigate("/");
        return;
      }
    }
    start_reveal();
    return () => {
      cancelled = true;
      ws?.close();
    };
  }, [code, name, navigate]);

  useEffect(() => {
    if (!code || !getReveal(code)) {
      setFlashMessage("Page not found");
      navigate("/");
    }
  }, [code, navigate]);

  const restaurantsSlideIndex = reveal
    ? Object.keys(reveal.personality_lines).length + 2
    : -1;

  useEffect(() => {
    if (!reveal || step === restaurantsSlideIndex) return;

    const timer = setTimeout(() => {
      setStep((prev) => prev + 1);
    }, 4000);

    return () => clearTimeout(timer);
  }, [step, reveal, restaurantsSlideIndex]);

  function renderLines(text: string, className: string) {
    return text.split("\n").map((line, i) => (
      <p key={i} className={className}>
        {line}
      </p>
    ));
  }

  if (!reveal) return null;

  const slides = [
    ...Object.entries(reveal.personality_lines).map(([person, line]) => ({
      type: "personality",
      person,
      line,
    })),
    { type: "agreements" },
    { type: "conflicts" },
    { type: "restaurants" },
  ];

  const currentSlide = slides[step] as
    | { type: "personality"; person: string; line: string }
    | { type: "agreements" }
    | { type: "conflicts" }
    | { type: "restaurants" };

  async function handleEndSession() {
    setError("");
    if (!code || !getParticipantName(code)) return;
    const trimmedName = name.trim();
    const sessionCode = code.trim().toUpperCase();
    try {
      const response = await axios.post(
        `${API_BASE}/end-session/${sessionCode}`,
        {
          host_name: trimmedName,
        },
      );
      setFlashMessage("Session ended");
      clearReveal(sessionCode);
      navigate(`/`);
    } catch (err) {
      if (axios.isAxiosError(err) && err.response) {
        setError(err.response.data.detail);
      } else {
        setError("Failed to end session, try again later");
      }
    }
  }
  
  return (
    <div className="flex flex-col items-center justify-center h-screen">
      {currentSlide.type === "personality" && (
        <div className="flex flex-col items-center gap-2 text-center">
          <h2 className="text-4xl font-black text-green-800">
            {currentSlide.person}
          </h2>
          <div className="max-w-2xl px-6 text-center">
            {renderLines(
              currentSlide.line,
              "text-xl text-gray-600 text-balance leading-snug mb-2 last:mb-0",
            )}
          </div>
        </div>
      )}
      {currentSlide.type === "agreements" && (
        <div className="flex flex-col items-center gap-2 text-center">
          <h2 className="text-4xl font-black text-green-800">Agreements</h2>
          <div className="max-w-2xl px-6 text-center">
            {renderLines(
              reveal.agreements,
              "text-xl text-gray-600 text-balance leading-snug mb-2 last:mb-0",
            )}
          </div>
        </div>
      )}
      {currentSlide.type === "conflicts" && (
        <div className="flex flex-col items-center gap-2 text-center">
          <h2 className="text-4xl font-black text-green-800">Conflicts</h2>
          <div className="max-w-2xl px-6 text-center">
            {renderLines(
              reveal.conflicts,
              "text-xl text-gray-600 text-balance leading-snug mb-2 last:mb-0",
            )}
          </div>
        </div>
      )}
      {currentSlide.type === "restaurants" && (
        <div className="flex flex-col items-center gap-4">
          <h2 className="text-3xl font-black text-green-800 mb-4">
            Here are our final restaurants!
          </h2>
          <div className="overflow-hidden p-4 w-full" ref={emblaRef}>
            <div className="flex w-full">
              {[reveal.primary, ...reveal.backups].map((restaurant, index) => (
                <div
                  key={index}
                  className="flex-[0_0_100%] min-w-0 flex justify-center"
                >
                  <RestaurantCard
                    restaurant={restaurant}
                    isPrimary={index === 0}
                  />
                </div>
              ))}
            </div>
          </div>
          <div className="flex gap-4">
            <Button label="←" onClick={() => emblaApi?.scrollPrev()} />
            <Button label="→" onClick={() => emblaApi?.scrollNext()} />
          </div>
          {name === host && (
            <div>
              <Button label="End session" onClick={handleEndSession} />
              <ErrorMessage message={error} />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
