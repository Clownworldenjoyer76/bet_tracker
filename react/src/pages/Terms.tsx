import "./Terms.css";
import termsHtml from "./terms-content.html?raw";

export default function Terms() {
  return (
    <main className="info-page terms-page">
      <div className="info-content terms-content" dangerouslySetInnerHTML={{ __html: termsHtml }} />
    </main>
  );
}