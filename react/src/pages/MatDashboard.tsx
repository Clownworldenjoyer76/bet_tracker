import "../../../app/frontend/src/assets/css/pages/mat.css";

const links = [
  ["Daily Picks", "/the_picks.html"],
  ["Scores", "/live_scores.html"],
  ["Kelly", "/kelly_calculator.html"],
  ["Standings", "/standings.html"],
  ["Bet History", "/bet_history.html"],
  ["Games Today", "/games_today.html"],
] as const;

export default function MatDashboard() {
  return (
    <main className="container">
      <h1>Dashboard</h1>
      <nav aria-label="Dashboard shortcuts">
        {links.map(([label, href]) => <p key={href}><a href={href}>{label}</a></p>)}
      </nav>
    </main>
  );
}
