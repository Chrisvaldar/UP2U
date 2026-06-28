import { useState, useEffect } from "react";
import { useNavigate, useParams, useLocation } from "react-router-dom";
import useEmblaCarousel from "embla-carousel-react";
import Button from "../components/Button";
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
  const [emblaRef, emblaApi] = useEmblaCarousel({ loop: false });

  useEffect(() => {
    if (reveal) {
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
        if (session.data?.error) {
          setFlashMessage("Page not found");
          navigate("/");
          return;
        }

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
      } catch {
        if (!cancelled) {
          setFlashMessage("Network failed");
          navigate("/");
        }
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
      if (response.data?.error) {
        setError(response.data.error);
        return;
      }
      setFlashMessage("Session ended");
      clearReveal(sessionCode);
      navigate(`/`);
    } catch {
      setError("Failed to end session, try again later");
    }
  }
  return (
    <div className="flex flex-col items-center justify-center h-screen">
      {currentSlide.type === "personality" && (
        <div className="flex flex-col items-center gap-2 text-center">
          <h2 className="text-4xl font-black text-green-800">
            {currentSlide.person}
          </h2>
          <p className="text-xl text-gray-600 max-w-md whitespace-pre-line">
            {currentSlide.line}
          </p>
        </div>
      )}
      {currentSlide.type === "agreements" && (
        <div className="max-w-md text-center px-6">
          <h2 className="text-3xl font-black text-green-800 whitespace-pre-line">
            {reveal.agreements}
          </h2>
        </div>
      )}
      {currentSlide.type === "conflicts" && (
        <div className="max-w-md text-center px-6">
          <h2 className="text-3xl font-black text-green-800 whitespace-pre-line">
            {reveal.conflicts}
          </h2>
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
                  <div className="bg-white rounded-2xl shadow-lg p-8 max-w-md w-full flex flex-col gap-4">
                    <h2 className="text-2xl font-black text-green-800">
                      {restaurant.name}
                    </h2>
                    <p className="text-gray-600">{restaurant.reason}</p>
                    <a
                      href={restaurant.maps_link}
                      target="_blank"
                      className="text-green-700 font-semibold underline"
                    >
                      Open in Maps
                    </a>
                  </div>
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
