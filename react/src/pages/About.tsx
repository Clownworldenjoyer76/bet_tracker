import InfoPageLayout from "../components/InfoPageLayout";

export default function About() {
  return (
    <InfoPageLayout title="About SportsModelHub">
      <section><h2>What this site provides</h2><p>SportsModelHub brings together sports schedules, game data, betting-model analysis, and historical results in one place.</p></section>
      <section><h2>How to use the data</h2><p>Explore the dashboards by league, review model results and historical performance, and verify game information against official sources before making decisions.</p></section>
      <section><h2>Limits of model output</h2><p>Model estimates are not guarantees. Games, odds, injuries, data sources, and model assumptions can change.</p></section>
      <p><a href="/contact.html">Contact / Support</a></p>
    </InfoPageLayout>
  );
}
