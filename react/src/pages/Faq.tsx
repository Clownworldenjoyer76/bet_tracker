import InfoPageLayout from "../components/InfoPageLayout";

export default function Faq() {
  return (
    <InfoPageLayout title="Frequently Asked Questions">
      <section><h2>What does SportsModelHub show?</h2><p>Dashboards for games, scores, league standings, model picks, prop analysis, and recorded outcomes, depending on data availability.</p></section>
      <section><h2>Why is a dashboard empty?</h2><p>Some leagues or markets do not have connected or recent data. An empty view does not mean a model has predicted no action.</p></section>
      <section><h2>Are model picks guarantees?</h2><p>No. Estimates and historical results are not guarantees.</p></section>
      <section><h2>How do I report a problem?</h2><p>Use Contact / Support and include the page URL and a description of the issue.</p></section>
      <p><a href="/contact.html">Contact / Support</a></p>
    </InfoPageLayout>
  );
}
