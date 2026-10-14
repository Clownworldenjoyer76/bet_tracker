import InfoPageLayout from "../components/InfoPageLayout";

export default function Disclaimer() {
  return (
    <InfoPageLayout title="Disclaimer">
      <section><h2>Informational purpose</h2><p>The dashboards and model outputs are provided for information and entertainment, not as betting, financial, or legal advice.</p></section>
      <section><h2>No guaranteed outcomes</h2><p>Predictions, probabilities, past performance, and historical statistics do not guarantee future results. Data may be delayed, incomplete, or inaccurate.</p></section>
      <section><h2>Your decisions</h2><p>Independent verification and responsible decision-making remain important. Do not risk money you cannot afford to lose.</p></section>
      <p><a href="/contact.html">Contact / Support</a></p>
    </InfoPageLayout>
  );
}
