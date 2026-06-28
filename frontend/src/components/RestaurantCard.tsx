import { API_BASE } from "@/lib/config";
import type { Restaurant } from "@/lib/session";
import useEmblaCarousel from "embla-carousel-react";

type RestaurantCardProps = {
  restaurant: Restaurant;
  isPrimary?: boolean;
};

export default function RestaurantCard({
  restaurant,
  isPrimary,
}: RestaurantCardProps) {
  const [emblaRef, emblaApi] = useEmblaCarousel({ loop: true });
  return (
    <div className="bg-white rounded-2xl shadow-lg p-8 max-w-md w-full flex flex-col gap-4">
      {restaurant.photo_urls && (
        <div className="overflow-hidden relative rounded-xl" ref={emblaRef}>
          <div className="flex">
            {restaurant.photo_urls.map((url, i) => (
              <div key={i} className="flex-[0_0_100%] min-w-0">
                <img
                  className="w-full object-cover h-60"
                  src={`${API_BASE}${url}`}
                />
              </div>
            ))}
          </div>
          <button
            className="flex items-center justify-center absolute left-2 top-1/2 -translate-y-1/2 bg-black/80 text-white rounded-full px-2 py-1"
            onClick={() => emblaApi?.scrollPrev()}
          >
            ←
          </button>
          <button
            className="flex items-center justify-center absolute right-2 top-1/2 -translate-y-1/2 bg-black/80 text-white rounded-full px-2 py-1"
            onClick={() => emblaApi?.scrollNext()}
          >
            →
          </button>
          {isPrimary && (
            <span className="absolute top-3 left-3 bg-green-600 text-white text-sm font-bold px-3 py-1 rounded-full">
              Best Match!
            </span>
          )}
        </div>
      )}
      <div className="flex items-center gap-2">
        <h2 className="text-2xl font-black text-green-800">
          {restaurant.name}
        </h2>
      </div>
      <p className="text-gray-600">{restaurant.reason}</p>
      <a
        href={restaurant.maps_link}
        target="_blank"
        className="text-green-700 font-semibold underline"
      >
        Open in Maps
      </a>
    </div>
  );
}
