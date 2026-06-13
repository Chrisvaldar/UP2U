import './App.css'
import {Route, Routes} from "react-router-dom"
import HomePage from "./pages/HomePage"
import Lobby from "./pages/Lobby"
import Survey from "./pages/Survey"
import Reveal from "./pages/Reveal"

function App() {

  return (
   <Routes>
    <Route path="/" element={<HomePage />} />
    <Route path="/lobby/:code" element={<Lobby />} />
    <Route path="/survey/:code" element={<Survey />} />
    <Route path="/reveal/:code" element={<Reveal />} />
   </Routes>
  )
}

export default App
