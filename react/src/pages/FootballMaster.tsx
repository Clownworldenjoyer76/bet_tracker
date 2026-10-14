import "../../../app/frontend/src/assets/css/generated/sport-summary-dashboard.css";
import "../../../app/frontend/src/assets/css/pages/football_dashboard.css";

const leagues = [
  { name: "NFL", href: "/nfl_dashboard.html" },
  { name: "College Football", href: "/ncaaf_dashboard.html" },
] as const;

export default function FootballMaster() {
  return (
    <main className="master-wrap">
      <div className="master-head">
        <h1>Football Analytics</h1>
        <p className="master-sub">NFL and college football dashboards</p>
      </div>
      <div className="league-grid-master">
        {leagues.map(({ name, href }) => (
          <a className="league-card" href={href} key={href}>
            <span className="league-name">{name}</span>
            <span className="league-link">OPEN DASHBOARD →</span>
          </a>
        ))}
      </div>
    </main>
  );
}
