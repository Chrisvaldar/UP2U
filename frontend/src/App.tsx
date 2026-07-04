import "./App.css";
import { Route, Routes } from "react-router-dom";
import HomePage from "./pages/HomePage";
import Lobby from "./pages/Lobby";
import Survey from "./pages/Survey";
import Reveal from "./pages/Reveal";
import { APIProvider } from "@vis.gl/react-google-maps";

/**
 * Root application shell with Google Maps provider and route definitions.
 *
 * @returns Routed pages for home, lobby, survey, and reveal flows.
 */
function App() {
  return (
    <APIProvider apiKey={import.meta.env.VITE_GOOGLE_MAPS_API_KEY}>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/lobby/:code" element={<Lobby />} />
        <Route path="/survey/:code" element={<Survey />} />
        <Route path="/reveal/:code" element={<Reveal />} />
      </Routes>
    </APIProvider>
  );
}

export default App;
