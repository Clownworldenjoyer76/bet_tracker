import "./Privacy.css";
import privacyHtml from "./privacy-content.html?raw";

export default function Privacy() {
  return (
    <main className="info-page privacy-page">
      <div className="info-content privacy-content" dangerouslySetInnerHTML={{ __html: privacyHtml }} />
    </main>
  );
}