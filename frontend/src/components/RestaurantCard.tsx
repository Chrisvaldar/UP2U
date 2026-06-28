import { API_BASE } from "@/lib/config";
import type { Restaurant } from "@/lib/session";

type RestaurantCardProps = {
  restaurant: Restaurant;
};

export default function RestaurantCard({ restaurant }: RestaurantCardProps) {
  return (
    <div className="bg-white rounded-2xl shadow-lg p-8 max-w-md w-full flex flex-col gap-4">
      {restaurant.photo_url && (
        <img
          className="w-full rounded-xl object-cover h-48"
          src={`${API_BASE}${restaurant.photo_url}`}
        />
      )}
      <h2 className="text-2xl font-black text-green-800">{restaurant.name}</h2>
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
