import { render, screen, waitFor } from "@testing-library/react";
import Lobby from "./Lobby";
import { vi } from "vitest";
import axios from "axios";
import { userEvent } from "@testing-library/user-event";
import { MockWebSocket } from "../test-utils/mockWebSocket";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { saveParticipantName } from "@/lib/session";
import { act } from "@testing-library/react";

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

vi.mock("../components/LocationAutocomplete", () => ({
  LocationAutocomplete: ({ onPlaceSelect }: any) => (
    <button
      onClick={() =>
        onPlaceSelect({ location: { lat: () => -37.8, lng: () => 144.9 } })
      }
    >
      Select Location
    </button>
  ),
}));

afterEach(() => {
  vi.clearAllMocks();
});

beforeEach(() => {
  globalThis.WebSocket = MockWebSocket as any;
  MockWebSocket.instances = [];
  sessionStorage.clear();
});

function renderLobby(name: string) {
  saveParticipantName("ABC123", name);
  render(
    <MemoryRouter
      initialEntries={[{ pathname: "/lobby/ABC123", state: { name } }]}
    >
      <Routes>
        <Route path="/lobby/:code" element={<Lobby />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("Lobby", () => {
  it("renders session code and host", async () => {
    vi.mocked(axios.get).mockResolvedValue({
      data: { host: "Chris", participants: ["Chris"] },
    });

    renderLobby("Chris");
    await waitFor(() => {
      expect(screen.getByText("ABC123")).toBeInTheDocument();
      expect(screen.getByText("Host: Chris")).toBeInTheDocument();
    });
  });

  it("start session available for host", async () => {
    vi.mocked(axios.get).mockResolvedValue({
      data: { host: "Chris", participants: ["Chris"] },
    });
    renderLobby("Chris");
    await waitFor(() => {
      expect(screen.getByText("Start Session")).toBeInTheDocument();
    });
  });

  it("start session not available for non-host", async () => {
    vi.mocked(axios.get).mockResolvedValue({
      data: { host: "Chris", participants: ["Chris"] },
    });
    renderLobby("test");
    await waitFor(() => {
      expect(screen.getByText(/Waiting for host to start/)).toBeInTheDocument();
    });
  });

  it("participant list updates on participant_joined event", async () => {
    vi.mocked(axios.get).mockResolvedValue({
      data: { host: "Chris", participants: ["Chris"] },
    });
    renderLobby("Chris");
    await waitFor(() => {
      expect(screen.getByText("Chris")).toBeInTheDocument();
    });

    const ws = MockWebSocket.instances[0];
    act(() => {
      ws.onmessage!({
        data: JSON.stringify({
          type: "participant_joined",
          data: { participants: ["Chris", "Sarah"] },
        }),
      } as MessageEvent);
    });

    await waitFor(() => {
      expect(screen.getByText("Sarah")).toBeInTheDocument();
    });
  });

  it("navigates to survey on session_started event", async () => {
    vi.mocked(axios.get).mockResolvedValue({
      data: { host: "Chris", participants: ["Chris"] },
    });
    renderLobby("Chris");
    await waitFor(() => {
      expect(screen.getByText("Chris")).toBeInTheDocument();
    });

    const ws = MockWebSocket.instances[0];
    ws.onmessage!({
      data: JSON.stringify({ type: "session_started", data: {} }),
    } as MessageEvent);

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith("/survey/ABC123", {
        state: { name: "Chris" },
      });
    });
  });

  it("redirects home when no participant name is stored", async () => {
    render(
      <MemoryRouter
        initialEntries={[
          { pathname: "/lobby/ABC123", state: { name: "Chris" } },
        ]}
      >
        <Routes>
          <Route path="/lobby/:code" element={<Lobby />} />
        </Routes>
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith("/");
    });
  });

  it("shows error message when start-session fails", async () => {
    vi.mocked(axios.get).mockResolvedValue({
      data: { host: "Chris", participants: ["Chris"] },
    });
    vi.mocked(axios.isAxiosError).mockReturnValue(true);
    vi.mocked(axios.post).mockRejectedValue({
      response: { data: { detail: "Only the host can start the session." } },
    });

    renderLobby("Chris");
    await waitFor(() => {
      expect(screen.getByText("Start Session")).toBeInTheDocument();
    });

    await user.click(screen.getByText("Select Location"));
    await user.click(screen.getByText("Start Session"));

    await waitFor(() => {
      expect(
        screen.getByText("Only the host can start the session."),
      ).toBeInTheDocument();
    });
  });

  it("shows error message when WebSocket connection fails", async () => {
    vi.mocked(axios.get).mockResolvedValue({
      data: { host: "Chris", participants: ["Chris"] },
    });
    renderLobby("Chris");
    await waitFor(() => {
      expect(screen.getByText("Chris")).toBeInTheDocument();
    });
    const ws = MockWebSocket.instances[0];
    act(() => {
      ws.onerror!({} as Event);
    });

    await waitFor(() => {
      expect(
        screen.getByText(
          "Lost the live lobby connection. Refresh to reconnect.",
        ),
      ).toBeInTheDocument();
    });
  });
});
