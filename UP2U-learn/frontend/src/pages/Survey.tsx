import { useState, useEffect } from "react";
import axios from "axios";
import { useNavigate, useParams, useLocation } from "react-router-dom";

export default function Survey() {
  const [hunger, setHunger] = useState(3);
  const [vibe, setVibe] = useState("");
  const [cuisinesRanked, setCuisinesRanked] = useState([]);
  const [travelDistance, setTravelDistance] = useState("");
  const [dietary, setDietary] = useState([]);
  return <div>Survey</div>;
}
