import { useState, useEffect } from "react";
import axios from "axios";
import { useNavigate, useParams, useLocation } from "react-router-dom";

export default function Reveal() {
  const name = useLocation().state?.name;
  const reveal = useLocation().state?.reveal;

  return <div>Reveal</div>;
}
