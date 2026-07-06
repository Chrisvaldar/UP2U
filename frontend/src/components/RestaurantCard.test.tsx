import { render, screen } from "@testing-library/react";
import RestaurantCard from "./RestaurantCard";
import type { Restaurant } from "@/lib/session";

const mockRestaurant: Restaurant = {
  name: "Chin Chin",
  reason: "Loud, fun, and the laksa slaps.",
  maps_link: "https://www.google.com/maps/place/?q=place_id:test123",
};

describe("RestaurantCard", () => {
  it("renders the restaurant name", () => {
    render(<RestaurantCard restaurant={mockRestaurant} />);
    expect(screen.getByText("Chin Chin")).toBeInTheDocument();
  });
});
