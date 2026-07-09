<!-- Improved compatibility of back to top link: See: https://github.com/othneildrew/Best-README-Template/pull/73 -->
<a id="readme-top"></a>



<!-- PROJECT SHIELDS -->
[![Contributors][contributors-shield]][contributors-url]
[![Forks][forks-shield]][forks-url]
[![Stargazers][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url]
[![Build][build-shield]][build-url]
[![LinkedIn][linkedin-shield]][linkedin-url]



<!-- PROJECT LOGO -->
<br />
<div align="center">
  <h3 align="center">UP2U</h3>

  <p align="center">
    Friends stuck deciding where to eat? Create a session, everyone answers a quick survey, AI picks a spot and roasts the group a bit.
    <br />
    <a href="https://up2u-app.vercel.app/"><strong>Live Demo »</strong></a>
    <br />
    <br />
    <a href="https://up2u-app.vercel.app/">View Demo</a>
    &middot;
    <a href="https://github.com/Chrisvaldar/UP2U/issues/new?labels=bug">Report Bug</a>
    &middot;
    <a href="https://github.com/Chrisvaldar/UP2U/issues/new?labels=enhancement">Request Feature</a>
  </p>
</div>



<!-- TABLE OF CONTENTS -->
<details>
  <summary>Table of Contents</summary>
  <ol>
    <li>
      <a href="#about-the-project">About The Project</a>
      <ul>
        <li><a href="#built-with">Built With</a></li>
      </ul>
    </li>
    <li>
      <a href="#getting-started">Getting Started</a>
      <ul>
        <li><a href="#prerequisites">Prerequisites</a></li>
        <li><a href="#installation">Installation</a></li>
      </ul>
    </li>
    <li><a href="#usage">Usage</a></li>
    <li><a href="#roadmap">Roadmap</a></li>
    <li><a href="#contributing">Contributing</a></li>
    <li><a href="#contact">Contact</a></li>
    <li><a href="#acknowledgments">Acknowledgments</a></li>
  </ol>
</details>



<!-- ABOUT THE PROJECT -->
## About The Project

UP2U is a real-time group dining picker. Host makes a room, friends join with a code, everyone fills preferences, then you get a reveal with personality lines plus a restaurant (and backups).

How a session goes:

* **Home** — create or join with a 6-char code
* **Lobby** — wait for people, host sets location, starts
* **Survey** — hunger, vibe, cuisine ranking, distance, diet
* **Reveal** — AI group take + restaurant carousel

Group food decisions suck. This turns "idk where do you wanna go" into one shared pick.

**Live app:** [https://up2u-app.vercel.app/](https://up2u-app.vercel.app/)

<p align="right">(<a href="#readme-top">back to top</a>)</p>



### Built With

* [![React][React.js]][React-url]
* [![Vite][Vite.js]][Vite-url]
* [![TypeScript][TypeScript]][TypeScript-url]
* [![Tailwind CSS][TailwindCSS]][Tailwind-url]
* [![FastAPI][FastAPI]][FastAPI-url]
* [![Redis][Redis]][Redis-url]
* [![Google Maps][GoogleMaps]][GoogleMaps-url]
* [![Gemini][Gemini]][Gemini-url]

Reveal generation uses Gemini by default, with an optional Groq fallback if Gemini is rate-limited or down.

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- GETTING STARTED -->
## Getting Started

Spin up a local copy with Redis, the FastAPI backend, and the Vite frontend.

### Prerequisites

* Node.js (CI uses 22)
* Python 3.13
* Redis (Docker one-liner below is fine)
* API keys: Google Maps (browser), Google Places (server), Gemini; Groq optional

**Google Places needs two keys, not one.** Mixing them up gets a 403 from Google that the backend surfaces as a 502.

| Key | Env var | Restrictions |
|-----|---------|--------------|
| Browser | `VITE_GOOGLE_MAPS_API_KEY` | Website referrers (Vercel + `http://localhost:5173/*`) |
| Server | `GOOGLE_PLACES_API_KEY` | No referrer restriction; restrict by API (Places API New + Photo Media) |

### Installation

1. Clone the repo
   ```sh
   git clone https://github.com/Chrisvaldar/UP2U.git
   cd UP2U
   ```
2. Start Redis
   ```powershell
   docker run -d -p 6379:6379 redis
   ```
3. Backend
   ```powershell
   cd backend
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   copy .env.example .env
   ```
   Fill in `backend/.env`:
   ```text
   REDIS_URL=redis://localhost:6379
   GOOGLE_PLACES_API_KEY=
   GEMINI_API_KEY=
   GROQ_API_KEY=
   DEBUG=true
   ```
   Then run:
   ```powershell
   uvicorn app.main:app --reload
   ```
4. Frontend (new terminal)
   ```powershell
   cd frontend
   npm install
   copy .env.example .env
   ```
   Fill in `frontend/.env`:
   ```text
   VITE_GOOGLE_MAPS_API_KEY=
   VITE_API_BASE=http://127.0.0.1:8000
   ```
   (`VITE_API_BASE` is optional locally; it defaults to `http://127.0.0.1:8000`.)
   Then run:
   ```powershell
   npm.cmd run dev
   ```
5. Open the Vite URL (usually `http://localhost:5173`) and create a session.

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- USAGE EXAMPLES -->
## Usage

1. Open the app, create a session, share the code
2. Friends join from Home with the same code
3. Host picks a location in Lobby, hits start
4. Everyone does the survey
5. When the last person submits, the reveal drops for everyone over WebSocket
6. Host can retry if reveal fails, or end the session when you are done

API reference (auto-generated by FastAPI): [https://up2u-production.up.railway.app/docs](https://up2u-production.up.railway.app/docs)

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- ROADMAP -->
## Roadmap

- [x] Create/join sessions with live lobby
- [x] Preference survey + group ranking
- [x] AI reveal with restaurant picks + photos
- [x] Deploy (Vercel frontend, Railway backend/Redis)
- [x] Test suite in place (41 frontend, 29 backend)
- [ ] Multi-instance WebSocket support (right now in-memory, one backend instance)
- [ ] Stronger frontend test coverage on edge cases (beyond the current 41)
- [ ] Reveal carousel index surviving refresh
- [ ] Auth, share links, and other polish later

See the [open issues](https://github.com/Chrisvaldar/UP2U/issues) for a full list of proposed features (and known issues).

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- CONTRIBUTING -->
## Contributing

This is a personal project, but issues and PRs are welcome if you want to poke at it.

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- CONTACT -->
## Contact

Christopher Valensio Darsono - [@Chrisvaldar](https://github.com/Chrisvaldar) - christophervalensio1@gmail.com

In: [https://www.linkedin.com/in/christopher-darsono-bb8959355/](https://www.linkedin.com/in/christopher-darsono-bb8959355/)

Project Link: [https://github.com/Chrisvaldar/UP2U](https://github.com/Chrisvaldar/UP2U)

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- ACKNOWLEDGMENTS -->
## Acknowledgments

Docs and third-party stuff used on this project.

### APIs / services

* [Google Maps Platform](https://developers.google.com/maps)
* [Google Places API (New)](https://developers.google.com/maps/documentation/places/web-service)
* [Google Geocoding API](https://developers.google.com/maps/documentation/geocoding)
* [Google Gemini](https://ai.google.dev/gemini-api/docs)
* [Groq](https://console.groq.com/docs)
* [Redis](https://redis.io/docs/)
* [Vercel](https://vercel.com/docs)
* [Railway](https://docs.railway.com/)
* [Google Fonts (Quicksand)](https://fonts.google.com/specimen/Quicksand)
* [GitHub Actions](https://docs.github.com/en/actions)

### Frontend

* [React / React DOM](https://react.dev/)
* [Vite](https://vite.dev/)
* [TypeScript](https://www.typescriptlang.org/docs/)
* [React Router](https://reactrouter.com/)
* [Axios](https://axios-http.com/)
* [Tailwind CSS](https://tailwindcss.com/docs)
* [shadcn/ui](https://ui.shadcn.com/)
* [Radix UI](https://www.radix-ui.com/)
* [Lucide](https://lucide.dev/)
* [Embla Carousel](https://www.embla-carousel.com/)
* [dnd-kit](https://dndkit.com/)
* [@vis.gl/react-google-maps](https://visgl.github.io/react-google-maps/)
* [Geist (Fontsource)](https://fontsource.org/fonts/geist)
* [Vitest](https://vitest.dev/)
* [Testing Library](https://testing-library.com/docs/react-testing-library/intro/)
* [jsdom](https://github.com/jsdom/jsdom)
* [ESLint](https://eslint.org/)

### Backend

* [FastAPI](https://fastapi.tiangolo.com/)
* [Uvicorn](https://uvicorn.dev/)
* [redis (Python client)](https://redis.readthedocs.io/)
* [python-dotenv](https://github.com/theskumar/python-dotenv)
* [requests](https://requests.readthedocs.io/)
* [httpx](https://www.python-httpx.org/)
* [google-genai](https://googleapis.github.io/python-genai/)
* [groq](https://github.com/groq/groq-python)
* [slowapi](https://slowapi.readthedocs.io/en/latest/)
* [pytest](https://docs.pytest.org/)
* [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
* [fakeredis](https://fakeredis.readthedocs.io/)

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- MARKDOWN LINKS & IMAGES -->
<!-- https://www.markdownguide.org/basic-syntax/#reference-style-links -->
[contributors-shield]: https://img.shields.io/github/contributors/Chrisvaldar/UP2U.svg?style=for-the-badge
[contributors-url]: https://github.com/Chrisvaldar/UP2U/graphs/contributors
[forks-shield]: https://img.shields.io/github/forks/Chrisvaldar/UP2U.svg?style=for-the-badge
[forks-url]: https://github.com/Chrisvaldar/UP2U/network/members
[stars-shield]: https://img.shields.io/github/stars/Chrisvaldar/UP2U.svg?style=for-the-badge
[stars-url]: https://github.com/Chrisvaldar/UP2U/stargazers
[issues-shield]: https://img.shields.io/github/issues/Chrisvaldar/UP2U.svg?style=for-the-badge
[issues-url]: https://github.com/Chrisvaldar/UP2U/issues
[build-shield]: https://github.com/Chrisvaldar/UP2U/actions/workflows/UP2U.yaml/badge.svg
[build-url]: https://github.com/Chrisvaldar/UP2U/actions/workflows/UP2U.yaml
[linkedin-shield]: https://img.shields.io/badge/-LinkedIn-black.svg?style=for-the-badge&logo=linkedin&colorB=555
[linkedin-url]: https://linkedin.com/in/your_username
[React.js]: https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB
[React-url]: https://react.dev/
[Vite.js]: https://img.shields.io/badge/Vite-646CFF?style=for-the-badge&logo=vite&logoColor=white
[Vite-url]: https://vite.dev/
[TypeScript]: https://img.shields.io/badge/TypeScript-3178C6?style=for-the-badge&logo=typescript&logoColor=white
[TypeScript-url]: https://www.typescriptlang.org/
[TailwindCSS]: https://img.shields.io/badge/Tailwind_CSS-38B2F6?style=for-the-badge&logo=tailwindcss&logoColor=white
[Tailwind-url]: https://tailwindcss.com/
[FastAPI]: https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white
[FastAPI-url]: https://fastapi.tiangolo.com/
[Redis]: https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white
[Redis-url]: https://redis.io/
[GoogleMaps]: https://img.shields.io/badge/Google_Maps-4285F4?style=for-the-badge&logo=googlemaps&logoColor=white
[GoogleMaps-url]: https://developers.google.com/maps
[Gemini]: https://img.shields.io/badge/Gemini-8E75B2?style=for-the-badge&logo=googlegemini&logoColor=white
[Gemini-url]: https://ai.google.dev/
