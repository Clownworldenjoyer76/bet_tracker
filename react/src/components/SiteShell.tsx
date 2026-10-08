import { useEffect, type MouseEvent, type ReactNode } from "react";
import { useLocation, useNavigate } from "react-router";
import Footer from "./Footer";

declare global {
  interface Window {
    __smhReactNavScriptLoaded?: boolean;
  }
}

const REACT_ROUTES = new Set([
  "/teams.html",
  "/the_picks.html",
  "/prop_engine.html",
  "/props_nfl.html",
  "/standings.html",
  "/players.html",
  "/bet_history_daily.html",
  "/pipeline_health.html",
  "/news.html",
  "/kelly_calculator.html",
  "/injury_tracker.html",
  "/",
  "/index.html",
  "/games_today.html",
  "/live_scores.html",
  "/final_scores.html",
  "/nba_dashboard.html",
  "/ncaam_dashboard.html",
  "/basketball_dashboard.html",
  "/wnba_dashboard.html",
  "/soccer_dashboard.html",
  "/mlb_dashboard.html",
  "/baseball_dashboard.html",
  "/ufc_dashboard.html",
  "/nhl_dashboard.html",
  "/nfl_dashboard.html",
  "/bet_history.html",
  "/transactions.html",
]);

interface SiteShellProps {
  children: ReactNode;
}

export default function SiteShell({ children }: SiteShellProps) {
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    const isHome =
      location.pathname === "/" ||
      location.pathname === "/index.html";

    document.body.classList.toggle("smh-home-page", isHome);

    return () => {
      document.body.classList.remove("smh-home-page");
    };
  }, [location.pathname]);

  useEffect(() => {
    if (window.__smhReactNavScriptLoaded) return;

    window.__smhReactNavScriptLoaded = true;

    const script = document.createElement("script");
    script.src = "/assets/js/shared/nav.js";
    script.async = false;
    document.head.appendChild(script);
  }, []);

  const handleClickCapture = (event: MouseEvent<HTMLDivElement>) => {
    // SMH_FULL_RELOAD_CONTENT_ROUTES
    if (
      location.pathname === "/model_validation.html" ||
      location.pathname === "/manual_data.html" ||
      location.pathname === "/manual_venue_data.html"
    ) {
      return;
    }
    if (
      event.defaultPrevented ||
      event.button !== 0 ||
      event.metaKey ||
      event.ctrlKey ||
      event.shiftKey ||
      event.altKey
    ) return;

    const target = event.target;

    if (!(target instanceof Element)) return;

    const anchor = target.closest("a[href]");

    if (!(anchor instanceof HTMLAnchorElement)) return;

    if (anchor.target && anchor.target !== "_self") return;

    const href = anchor.getAttribute("href");

    if (!href) return;

    const url = new URL(href, window.location.href);

    if (url.origin !== window.location.origin) return;

    if (!REACT_ROUTES.has(url.pathname)) return;

    if (
      url.pathname === window.location.pathname &&
      url.search === window.location.search &&
      url.hash === window.location.hash
    ) {
      return;
    }

    event.preventDefault();

    navigate(
      `${url.pathname}${url.search}${url.hash}`,
      { viewTransition: true }
    );
  };

  return (
    <div
      className="smh-react-shell"
      onClickCapture={handleClickCapture}
    >
      <div className="smh-react-chrome">
        <div id="nav-placeholder" />
      </div>

      <div className="smh-react-page" role="main">
        {children}
      </div>

      <Footer />
    </div>
  );
}


















