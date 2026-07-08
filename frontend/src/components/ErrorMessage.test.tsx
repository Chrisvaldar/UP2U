import { render, screen } from "@testing-library/react";
import ErrorMessage from "./ErrorMessage";

describe("ErrorMessage", () => {
    it("does not render error message when message is empty", () => {
        const { container } = render(<ErrorMessage message="" />);
        expect(container.firstChild).toBeNull();
    })

    it("renders error message", () => {
        render(<ErrorMessage message="error" />);
        expect(screen.getByText("error")).toBeInTheDocument();
    })
})