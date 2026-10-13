import "../../../app/frontend/src/assets/css/generated/sport-summary-dashboard.css";
import "../../../app/frontend/src/assets/css/pages/football_dashboard.css";

const props = [
  { name: "Prop Engine", description: "Player prop analysis", href: "/prop_engine.html" },
  { name: "NFL Props", description: "Football prop markets", href: "/props_nfl.html" },
] as const;

export default function PropsMaster() {
  return (
    <main className="master-wrap">
      <div className="master-head">
        <h1>Player Props</h1>
        <p className="master-sub">Choose a prop analytics page</p>
      </div>
      <div className="league-grid-master">
        {props.map(({ name, description, href }) => (
          <a className="league-card" href={href} key={href}>
            <span className="league-name">{name}</span>
            <span className="league-link">{description} →</span>
          </a>
        ))}
      </div>
    </main>
  );
}
