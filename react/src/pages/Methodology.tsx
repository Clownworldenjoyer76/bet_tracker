import InfoPageLayout from "../components/InfoPageLayout";

export default function Methodology() {
  return (
    <InfoPageLayout title="Methodology">
      <section><h2>How to interpret the dashboard</h2><p>The site presents estimates and historical summaries generated from underlying sports data. Individual pages may use different models, market definitions, and data refresh schedules.</p></section>
      <section><h2>Accuracy and validation</h2><p>Review the Model Validation and Bet History pages for available historical results. Sample sizes, market conditions, and selection effects can materially affect apparent performance.</p></section>
      <section><h2>Model details</h2><p>A model-specific methodology, inputs, fitting method, and validation protocol are not published on this page; avoid inferring a guaranteed edge from dashboard estimates.</p></section>
      <p><a href="/contact.html">Contact / Support</a></p>
    </InfoPageLayout>
  );
}
