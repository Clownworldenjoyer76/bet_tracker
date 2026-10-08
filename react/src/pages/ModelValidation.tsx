import LegacyHtmlPage from "../components/LegacyHtmlPage";
import pageHtml from "../../../app/frontend/src/pages/model_validation.html?raw";
import "../../../app/frontend/src/assets/css/pages/model_validation.css";

const SCRIPTS = [
  "/assets/js/shared/kelly-league-availability.js",
  "/assets/js/shared/league_nav.js",
  "/assets/js/pages/model_validation.2.js",
  "/assets/js/model-validation/config.js",
  "/assets/js/model-validation/sources.js",
  "/assets/js/model-validation/csv.js",
  "/assets/js/model-validation/normalize.js",
  "/assets/js/model-validation/app.js",
] as const;

export default function ModelValidation() {
  return <LegacyHtmlPage html={pageHtml} scripts={SCRIPTS} />;
}
