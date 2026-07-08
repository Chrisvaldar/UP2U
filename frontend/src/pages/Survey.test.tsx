import { render, screen, waitFor } from "@testing-library/react";
import Survey from "./Survey";
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

afterEach(() => {
  vi.clearAllMocks();
});

beforeEach(() => {
  globalThis.WebSocket = MockWebSocket as any;
  MockWebSocket.instances = [];
  sessionStorage.clear();
});

function renderSurvey(name: string) {
  saveParticipantName("ABC123", name);
  render(
    <MemoryRouter
      initialEntries={[{ pathname: "/survey/ABC123", state: { name } }]}
    >
      <Routes>
        <Route path="/survey/:code" element={<Survey />} />
      </Routes>
    </MemoryRouter>,
  );
}

async function goToStep4() {
  await waitFor(() => {
    expect(
      screen.getByText("How hungry are you right now? (1-5)"),
    ).toBeInTheDocument();
  });
  await user.click(screen.getByText("Next"));

  await waitFor(() => {
    expect(
      screen.getByText("What's the vibe you're looking for?"),
    ).toBeInTheDocument();
  });
  await user.click(screen.getByText("Casual"));
  await user.click(screen.getByText("Next"));

  await waitFor(() => {
    expect(
      screen.getByText("What kind of food are you feeling right now?"),
    ).toBeInTheDocument();
  });
  await user.click(screen.getByText("Next"));

  await waitFor(() => {
    expect(
      screen.getByText("What kind of travel are we comfortable with?"),
    ).toBeInTheDocument();
  });
  await user.click(screen.getByText("Short walk (<500m)"));
  await user.click(screen.getByText("Next"));

  await waitFor(() => {
    expect(
      screen.getByText("Any dietary requirements? (Multi-select)"),
    ).toBeInTheDocument();
  });
}

describe("Survey", () => {
  it("renders step 0 on mount", async () => {
    vi.mocked(axios.get).mockResolvedValue({
      data: {
        host: "Chris",
        status: "active",
        participants: ["Chris", "Sarah"],
        answers: {},
        cuisines: ["thai", "italian"],
      },
    });

    renderSurvey("Chris");

    await waitFor(() => {
      expect(
        screen.getByText("How hungry are you right now? (1-5)"),
      ).toBeInTheDocument();
    });
  });

  it("steps through the survey and submits, landing on waiting step", async () => {
    vi.mocked(axios.get).mockResolvedValue({
      data: {
        host: "Chris",
        status: "active",
        participants: ["Chris", "Sarah"],
        answers: {},
        cuisines: ["thai", "italian"],
      },
    });
    vi.mocked(axios.post).mockResolvedValue({ data: {} });

    renderSurvey("Chris");
    await goToStep4();
    await user.click(screen.getByText("Submit"));

    await waitFor(() => {
      expect(
        screen.getByText(/Waiting for others to submit/),
      ).toBeInTheDocument();
    });
  });

  it("shows error message when submit fails", async () => {
    vi.mocked(axios.get).mockResolvedValue({
      data: {
        host: "Chris",
        status: "active",
        participants: ["Chris", "Sarah"],
        answers: {},
        cuisines: ["thai", "italian"],
      },
    });
    vi.mocked(axios.isAxiosError).mockReturnValue(true);
    vi.mocked(axios.post).mockRejectedValue({
      response: { data: { detail: "Session not found" } },
    });

    renderSurvey("Chris");
    await goToStep4();
    await user.click(screen.getByText("Submit"));

    await waitFor(() => {
      expect(screen.getByText("Session not found")).toBeInTheDocument();
    });
  });

  it("navigates to reveal on reveal_ready event", async () => {
    vi.mocked(axios.get).mockResolvedValue({
      data: {
        host: "Chris",
        status: "active",
        participants: ["Chris", "Sarah"],
        answers: {},
        cuisines: ["thai", "italian"],
      },
    });

    renderSurvey("Chris");

    await waitFor(() => {
      expect(
        screen.getByText("How hungry are you right now? (1-5)"),
      ).toBeInTheDocument();
    });

    const ws = MockWebSocket.instances[0];
    const revealData = { primary: { name: "Test Restaurant" } };
    ws.onmessage!({
      data: JSON.stringify({ type: "reveal_ready", data: revealData }),
    } as MessageEvent);

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith("/reveal/ABC123", {
        state: { name: "Chris", reveal: revealData },
      });
    });
  });

  it("shows step 7 recovery UI for host on reveal_failed event", async () => {
    vi.mocked(axios.get).mockResolvedValue({
      data: {
        host: "Chris",
        status: "active",
        participants: ["Chris", "Sarah"],
        answers: {},
        cuisines: ["thai", "italian"],
      },
    });

    renderSurvey("Chris");

    await waitFor(() => {
      expect(
        screen.getByText("How hungry are you right now? (1-5)"),
      ).toBeInTheDocument();
    });

    const ws = MockWebSocket.instances[0];
    act(() => {
      ws.onmessage!({
        data: JSON.stringify({
          type: "reveal_failed",
          data: { error: "Oops! Reveal failed" },
        }),
      } as MessageEvent);
    });

    await waitFor(() => {
      expect(screen.getByText("Oops! Reveal failed")).toBeInTheDocument();
      expect(screen.getByText("Go back to lobby")).toBeInTheDocument();
      expect(screen.getByText("End session")).toBeInTheDocument();
    });
  });

  it("navigates home and sets flash message on session_ended event", async () => {
    vi.mocked(axios.get).mockResolvedValue({
      data: {
        host: "Chris",
        status: "active",
        participants: ["Chris", "Sarah"],
        answers: {},
        cuisines: ["thai", "italian"],
      },
    });

    renderSurvey("Chris");

    await waitFor(() => {
      expect(
        screen.getByText("How hungry are you right now? (1-5)"),
      ).toBeInTheDocument();
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
    });
  });

  it("updates submitted count and advances to step 6 on last answer_submitted event", async () => {
    vi.mocked(axios.get).mockResolvedValue({
      data: {
        host: "Chris",
        status: "active",
        participants: ["Chris", "Sarah"],
        answers: {},
        cuisines: ["thai", "italian"],
      },
    });

    renderSurvey("Chris");

    await waitFor(() => {
      expect(
        screen.getByText("How hungry are you right now? (1-5)"),
      ).toBeInTheDocument();
    });

    const ws = MockWebSocket.instances[0];
    act(() => {
      ws.onmessage!({
        data: JSON.stringify({
          type: "answer_submitted",
          data: { submitted: ["Chris", "Sarah"], total: 2 },
        }),
      } as MessageEvent);
    });

    await waitFor(() => {
      expect(
        screen.getByText("Finding nearby restaurants."),
      ).toBeInTheDocument();
    });
  });

  it("navigates to lobby on retrying event", async () => {
    vi.mocked(axios.get).mockResolvedValue({
      data: {
        host: "Chris",
        status: "active",
        participants: ["Chris", "Sarah"],
        answers: {},
        cuisines: ["thai", "italian"],
      },
    });

    renderSurvey("Chris");

    await waitFor(() => {
      expect(
        screen.getByText("How hungry are you right now? (1-5)"),
      ).toBeInTheDocument();
    });

    const ws = MockWebSocket.instances[0];
    act(() => {
      ws.onmessage!({
        data: JSON.stringify({ type: "retrying", data: {} }),
      } as MessageEvent);
    });

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith("/lobby/ABC123", {
        state: { name: "Chris" },
      });
    });
  });

  it("redirects home when no participant name is stored", async () => {
    render(
      <MemoryRouter
        initialEntries={[
          { pathname: "/survey/ABC123", state: { name: "Chris" } },
        ]}
      >
        <Routes>
          <Route path="/survey/:code" element={<Survey />} />
        </Routes>
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith("/");
    });
  });
});
