import { render, screen } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import Button from "./Button";
import type { ButtonProps } from "./Button";

const user = userEvent.setup();
const handleClick = vi.fn();

const mockButton: ButtonProps = {
  label: "test",
  onClick: handleClick,
  disabled: false,
};

afterEach(() => {
    vi.clearAllMocks();
  });

describe("Button", () => {
  it("renders button label", () => {
    render(<Button {...mockButton} />);
    expect(screen.getByText("test")).toBeInTheDocument();
  });

  it("button reacts to click", async () => {
    render(<Button {...mockButton} />);
    const button = screen.getByRole("button", { name: "test" });
    await user.click(button);
    expect(handleClick).toHaveBeenCalled();
  });

  it("button disabled correctly", () => {
    const newMockButton: ButtonProps = {...mockButton, disabled: true}
    render(<Button {...newMockButton} />);
    expect(screen.getByText("test")).toBeDisabled();
  });
});
