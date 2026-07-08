import { render, screen, waitFor } from "@testing-library/react";
import Reveal from "./Reveal";
import { vi } from "vitest";
import axios from "axios";
import { MockWebSocket } from "../test-utils/mockWebSocket";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { saveParticipantName, saveReveal, getReveal } from "@/lib/session";
import { act } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";

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
  vi.useRealTimers();
});

beforeEach(() => {
  globalThis.WebSocket = MockWebSocket as any;
  MockWebSocket.instances = [];
  sessionStorage.clear();
});

const sampleReveal = {
  personality_lines: {
    Chris: "Would literally eat anything right now.",
  },
  agreements: "Everyone's down for Italian!",
  conflicts: "Some want quick bites, some want a vibe.",
  primary: {
    name: "Test Restaurant",
    reason: "Great vibes and good food.",
    maps_link: "https://maps.google.com/?q=test",
  },
  backups: [
    {
      name: "Backup One",
      reason: "Solid backup.",
      maps_link: "https://maps.google.com/?q=b1",
    },
    {
      name: "Backup Two",
      reason: "Another solid backup.",
      maps_link: "https://maps.google.com/?q=b2",
    },
  ],
};

function renderReveal(name: string) {
  saveParticipantName("ABC123", name);
  render(
    <MemoryRouter
      initialEntries={[{ pathname: "/reveal/ABC123", state: { name } }]}
    >
      <Routes>
        <Route path="/reveal/:code" element={<Reveal />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("Reveal", () => {
  it("renders first personality slide when reveal is pre-seeded in sessionStorage", async () => {
    saveReveal("ABC123", sampleReveal);
    vi.mocked(axios.get).mockResolvedValue({
      data: { host: "Chris", status: "revealed" },
    });

    renderReveal("Chris");

    await waitFor(() => {
      expect(screen.getByText("Chris")).toBeInTheDocument();
      expect(
        screen.getByText("Would literally eat anything right now."),
      ).toBeInTheDocument();
    });
  });

  it("hydrates from API when sessionStorage is empty and status is revealed", async () => {
    vi.mocked(axios.get).mockResolvedValue({
      data: { host: "Chris", status: "revealed", reveal: sampleReveal },
    });

    renderReveal("Chris");

    await waitFor(() => {
      expect(screen.getByText("Chris")).toBeInTheDocument();
      expect(
        screen.getByText("Would literally eat anything right now."),
      ).toBeInTheDocument();
    });
  });

  it("redirects home when reveal cannot be recovered", async () => {
    vi.mocked(axios.get).mockResolvedValue({
      data: { host: "Chris", status: "active" },
    });

    renderReveal("Chris");

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith("/");
      expect(sessionStorage.getItem("up2u:message")).toBe("Page not found");
    });
  });

  it("navigates home and clears reveal on session_ended event", async () => {
    saveReveal("ABC123", sampleReveal);
    vi.mocked(axios.get).mockResolvedValue({
      data: { host: "Chris", status: "revealed" },
    });

    renderReveal("Chris");

    await waitFor(() => {
      expect(screen.getByText("Chris")).toBeInTheDocument();
    });

    const ws = MockWebSocket.instances[0];
    act(() => {
      ws.onmessage!({
        data: JSON.stringify({ type: "session_ended", data: {} }),
      } as MessageEvent);
    });

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith("/");
      expect(sessionStorage.getItem("up2u:message")).toBe("Session ended");
      expect(getReveal("ABC123")).toBeUndefined();
    });
  });

  it("shows network failed flash and redirects home on network error", async () => {
    vi.mocked(axios.isAxiosError).mockReturnValue(false);
    vi.mocked(axios.get).mockRejectedValue(new Error("Network Error"));

    renderReveal("Chris");

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith("/");
      expect(sessionStorage.getItem("up2u:message")).toBe("Network failed");
    });
  });

  it("auto-advances through slides and stops at restaurants", async () => {
    saveReveal("ABC123", sampleReveal);
    vi.mocked(axios.get).mockResolvedValue({
      data: { host: "Chris", status: "revealed" },
    });
    vi.useFakeTimers();

    renderReveal("Chris");

    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    expect(screen.getByText("Chris")).toBeInTheDocument();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(4000);
    });
    expect(screen.getByText("Agreements")).toBeInTheDocument();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(4000);
    });
    expect(screen.getByText("Conflicts")).toBeInTheDocument();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(4000);
    });
    expect(
      screen.getByText("Here are our final restaurants!"),
    ).toBeInTheDocument();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(4000);
    });
    expect(
      screen.getByText("Here are our final restaurants!"),
    ).toBeInTheDocument();
  });

  it("host end session happy path posts and navigates home", async () => {
    saveReveal("ABC123", sampleReveal);
    vi.mocked(axios.get).mockResolvedValue({
      data: { host: "Chris", status: "revealed" },
    });
    vi.mocked(axios.post).mockResolvedValue({ data: {} });
    vi.useFakeTimers();

    renderReveal("Chris");

    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    for (let i = 0; i < 3; i++) {
      await act(async () => {
        await vi.advanceTimersByTimeAsync(4000);
      });
    }
    expect(
      screen.getByText("Here are our final restaurants!"),
    ).toBeInTheDocument();

    vi.useRealTimers();

    await user.click(screen.getByText("End session"));

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith("/");
      expect(sessionStorage.getItem("up2u:message")).toBe("Session ended");
    });
  });

  it("shows error message when end-session fails", async () => {
    saveReveal("ABC123", sampleReveal);
    vi.mocked(axios.get).mockResolvedValue({
      data: { host: "Chris", status: "revealed" },
    });
    vi.mocked(axios.isAxiosError).mockReturnValue(true);
    vi.mocked(axios.post).mockRejectedValue({
      response: { data: { detail: "Only the host can end the session." } },
    });
    vi.useFakeTimers();

    renderReveal("Chris");

    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    for (let i = 0; i < 3; i++) {
      await act(async () => {
        await vi.advanceTimersByTimeAsync(4000);
      });
    }
    expect(
      screen.getByText("Here are our final restaurants!"),
    ).toBeInTheDocument();

    vi.useRealTimers();

    await user.click(screen.getByText("End session"));

    await waitFor(() => {
      expect(
        screen.getByText("Only the host can end the session."),
      ).toBeInTheDocument();
    });
  });

  it("does not show End session button for non-host", async () => {
    saveReveal("ABC123", sampleReveal);
    vi.mocked(axios.get).mockResolvedValue({
      data: { host: "Chris", status: "revealed" },
    });
    vi.useFakeTimers();

    renderReveal("Sarah");

    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    for (let i = 0; i < 3; i++) {
      await act(async () => {
        await vi.advanceTimersByTimeAsync(4000);
      });
    }
    expect(
      screen.getByText("Here are our final restaurants!"),
    ).toBeInTheDocument();

    expect(screen.queryByText("End session")).not.toBeInTheDocument();
  });
});
