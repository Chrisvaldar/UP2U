import { BrowserRouter, Routes, Route } from "react-router-dom";
import HomePage from "@/pages/HomePage";
import LobbyPage from "@/pages/LobbyPage";
import SurveyPage from "@/pages/SurveyPage";
import RevealPage from "@/pages/RevealPage";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/lobby/:code" element={<LobbyPage />} />
        <Route path="/survey/:code" element={<SurveyPage />} />
        <Route path="/reveal/:code" element={<RevealPage />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
