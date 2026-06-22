import { useState, useEffect } from "react";
import axios from "axios";
import { useNavigate, useParams, useLocation } from "react-router-dom";

export default function Reveal() {
  const name = useLocation().state?.name;
  const reveal = useLocation().state?.reveal;
  const [step, setStep] = useState(0);

  const slides = [
    ...Object.entries(reveal.personality_lines).map(([person, line]) => ({
      type: "personality",
      person,
      line
    })),
    { type: "agreements" },
    { type: "conflicts" },
    { type: "restaurants" }
  ];

  const currentSlide = slides[step] as any;

  useEffect(() => {
    if (slides[step]?.type === "restaurants") return;

    const timer = setTimeout(() => {
      setStep(step + 1);
    }, 4000);

    return () => clearTimeout(timer);
  }, [step]);
  return (
    <div className="flex flex-col items-center justify-center h-screen">
      {currentSlide.type === "personality" && (
        <div>
          <h2 className="text-3xl font-black text-green-800">
            {currentSlide.person}: {currentSlide.line}
          </h2>
        </div>
      )}
      {currentSlide.type === "agreements" && (
        <div>
          <h2>{reveal.agreements}</h2>
        </div>
      )}
      {currentSlide.type === "conflicts" && (
        <div>
          <h2>{reveal.conflicts}</h2>
        </div>
      )}
    </div>
  );
}
