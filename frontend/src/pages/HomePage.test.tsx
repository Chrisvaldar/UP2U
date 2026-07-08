import { render, screen, waitFor } from "@testing-library/react";
import HomePage from "./HomePage";
import { vi } from "vitest";
import axios from "axios";
import { userEvent } from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

const user = userEvent.setup();

vi.mock("axios");

const mockNavigate = vi.fn();

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

afterEach(() => {
  vi.clearAllMocks();
});

describe("HomePage", () => {
  it("renders components correctly", () => {
    render(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>,
    );
    expect(screen.getByText("Create Session")).toBeInTheDocument();
    expect(screen.getByText("Join Session")).toBeInTheDocument();
  });

  it("general create session works", async () => {
    vi.mocked(axios.post).mockResolvedValue({ data: { code: "ABC123" } });
    render(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>,
    );
    await user.click(screen.getByText("Create Session"));
    await user.type(screen.getByPlaceholderText("Name"), "Chris");
    await user.click(screen.getByText("Create"));

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith("/lobby/ABC123", {
        state: { name: "Chris" },
      });
    });
  });

  it("create session error message renders", async () => {
    vi.mocked(axios.post).mockRejectedValue(new Error("Network Error"));
    render(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>,
    );
    await user.click(screen.getByText("Create Session"));
    await user.type(screen.getByPlaceholderText("Name"), "Chris");
    await user.click(screen.getByText("Create"));

    await waitFor(() => {
      expect(
        screen.getByText(
          "Could not create a session. Check that the backend is running.",
        ),
      ).toBeInTheDocument();
    });
  });

  it("shows error when creating with no name", async () => {
    render(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>,
    );
    await user.click(screen.getByText("Create Session"));
    await user.click(screen.getByText("Create"));

    expect(screen.getByText("Enter your name first.")).toBeInTheDocument();
  });

  it("join session with waiting status works", async () => {
    vi.mocked(axios.post).mockResolvedValue({
      data: { code: "ABC123", status: "waiting" },
    });
    render(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>,
    );
    await user.click(screen.getByText("Join Session"));
    await user.type(screen.getByPlaceholderText("Name"), "Chris");
    await user.type(screen.getByPlaceholderText("Session Code"), "ABC123");
    await user.click(screen.getByText("Join"));

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith("/lobby/ABC123", {
        state: { name: "Chris" },
      });
    });
  });

  it("join session with active status works", async () => {
    vi.mocked(axios.post).mockResolvedValue({
      data: { code: "ABC123", status: "active" },
    });
    render(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>,
    );
    await user.click(screen.getByText("Join Session"));
    await user.type(screen.getByPlaceholderText("Name"), "Chris");
    await user.type(screen.getByPlaceholderText("Session Code"), "ABC123");
    await user.click(screen.getByText("Join"));

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith("/survey/ABC123", {
        state: { name: "Chris" },
      });
    });
  });
});
