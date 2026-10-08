import LegacyHtmlPage from "../components/LegacyHtmlPage";
import pageHtml from "../../../app/frontend/src/pages/manual_data.html?raw";
import "../../../app/frontend/src/assets/css/pages/manual_data.css";

const SCRIPTS = [
  "/assets/js/pages/manual_data.js",
] as const;

export default function ManualData() {
  return <LegacyHtmlPage html={pageHtml} scripts={SCRIPTS} />;
}
