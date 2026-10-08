import LegacyHtmlPage from "../components/LegacyHtmlPage";
import pageHtml from "../../../app/frontend/src/pages/manual_venue_data.html?raw";
import "../../../app/frontend/src/assets/css/pages/manual_venue_data.css";

const SCRIPTS = [
  "/assets/js/pages/manual_venue_data.js",
] as const;

export default function ManualVenueData() {
  return <LegacyHtmlPage html={pageHtml} scripts={SCRIPTS} />;
}
