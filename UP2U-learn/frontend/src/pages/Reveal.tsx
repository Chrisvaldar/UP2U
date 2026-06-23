import { useState, useEffect } from "react";
import axios from "axios";
import { useLocation } from "react-router-dom";
import useEmblaCarousel from "embla-carousel-react";
import Button from "../components/Button";

export default function Reveal() {
  const name = useLocation().state?.name;
  const reveal = useLocation().state?.reveal;
  const [step, setStep] = useState(0);
  const [emblaRef, emblaApi] = useEmblaCarousel({ loop: false });

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
        <div className="flex flex-col items-center gap-2 text-center">
          <h2 className="text-4xl font-black text-green-800">
            {currentSlide.person}
          </h2>
          <p className="text-xl text-gray-600">{currentSlide.line}</p>
        </div>
      )}
      {currentSlide.type === "agreements" && (
        <div>
          <h2 className="text-3xl font-black text-green-800">
            {reveal.agreements}
          </h2>
        </div>
      )}
      {currentSlide.type === "conflicts" && (
        <div>
          <h2 className="text-3xl font-black text-green-800">
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
        </div>
      )}
    </div>
  );
}
