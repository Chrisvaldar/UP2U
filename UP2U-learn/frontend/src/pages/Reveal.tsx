import { useState, useEffect } from "react";
import axios from "axios";
import { useNavigate, useParams, useLocation } from "react-router-dom";

export default function Reveal() {
  const name = useLocation().state?.name;
  const reveal = useLocation().state?.reveal;

  return (
    <div>
      <h1>Reveal</h1>

      <h2>{reveal.agreements}</h2>
      <h2>{reveal.conflicts}</h2>
      {Object.entries(reveal.personality_lines).map(([personName, line]) => (
        <h2 key={[personName, line]}>
          {personName}: {line}
        </h2>
      ))}

      <h1>Decision:</h1>
      <h2>
        {reveal.primary.name}: {reveal.primary.reason}
      </h2>
      <a target="_blank" href={reveal.primary.maps_link}>
        Open in Maps
      </a>

      <h1>Other Options:</h1>
      {reveal.backups.map(({ name, reason }) => (
        <h2 key={name}>
          {name}: {reason}
        </h2>
      ))}
    </div>
  );
}
