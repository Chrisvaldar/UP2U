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

  it("maps link working", () =>{
    render(<RestaurantCard restaurant={mockRestaurant} />);
    expect(screen.getByRole("link", { name: "Open in Maps" })).toHaveAttribute("href", mockRestaurant.maps_link)
  })

  it("does not show Best Match badge when there are no photos", () => {
    render(<RestaurantCard restaurant={mockRestaurant} isPrimary />);
    expect(screen.queryByText("Best Match!")).not.toBeInTheDocument();
  })

  it("shows Best Match badge when there is a photo", () => {
    const newMockRestaurant: Restaurant = {...mockRestaurant, photo_urls: ["/photo/test/0"]}
    render(<RestaurantCard restaurant={newMockRestaurant} isPrimary/>);
    expect(screen.getByText("Best Match!")).toBeInTheDocument();
  })
});
