import { Routes, Route } from "react-router";

import SiteShell from "./components/SiteShell";
import BaseballDashboard from "./pages/BaseballDashboard";
import GamesToday from "./pages/GamesToday";
import NbaDashboard from "./pages/NbaDashboard";
import NcaamDashboard from "./pages/NcaamDashboard";
import BasketballDashboard from "./pages/BasketballDashboard";
import WnbaDashboard from "./pages/WnbaDashboard";
import NhlDashboard from "./pages/NhlDashboard";
import UfcDashboard from "./pages/UfcDashboard";
import NflDashboard from "./pages/NflDashboard";
import CfbDashboard from "./pages/CfbDashboard";
import SoccerDashboard from "./pages/SoccerDashboard";
import LiveScores from "./pages/LiveScores";
import FinalScores from "./pages/FinalScores";
import News from "./pages/News";
import InjuryTracker from "./pages/InjuryTracker";
import Transactions from "./pages/Transactions";

import Teams from "./pages/Teams";
import Players from "./pages/Players";
import Standings from "./pages/Standings";
import ThePicks from "./pages/ThePicks";
import PropEngine from "./pages/PropEngine";
import PropsNfl from "./pages/PropsNfl";
import KellyCalculator from "./pages/KellyCalculator";
import BetHistory from "./pages/BetHistory";
import BetHistoryDaily from "./pages/BetHistoryDaily";
import ModelValidation from "./pages/ModelValidation";

function Home() {
  return <section aria-label="SportsModelHub home"><h1>SportsModelHub</h1><p>Sports analytics and model dashboards</p><p><a href="/games_today.html">Games today</a> · <a href="/the_picks.html">The Picks</a></p></section>;
}

import FootballMaster from "./pages/FootballMaster";
import PropsMaster from "./pages/PropsMaster";
import MatDashboard from "./pages/MatDashboard";
import About from "./pages/About";
import Accessibility from "./pages/Accessibility";
import Disclaimer from "./pages/Disclaimer";
import Faq from "./pages/Faq";
import Methodology from "./pages/Methodology";
import Privacy from "./pages/Privacy";
import ResponsibleGambling from "./pages/ResponsibleGambling";
import Terms from "./pages/Terms";
import ManualData from "./pages/ManualData";
import ManualVenueData from "./pages/ManualVenueData";
import PipelineHealth from "./pages/PipelineHealth";
export default function App() {
  return (
    <SiteShell>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/index.html" element={<Home />} />

        <Route
          path="/games_today.html"
          element={<GamesToday />}
        />

        <Route
          path="/mlb_dashboard.html"
          element={<BaseballDashboard />}
        />
        <Route path="/baseball_dashboard.html" element={<BaseballDashboard />} />

        <Route
          path="/ufc_dashboard.html"
          element={<UfcDashboard />}
        />

        <Route
          path="/nhl_dashboard.html"
          element={<NhlDashboard />}
        />
              <Route path="/nba_dashboard.html" element={<NbaDashboard />} />
        <Route path="/ncaam_dashboard.html" element={<NcaamDashboard />} />
        <Route path="/basketball_dashboard.html" element={<BasketballDashboard />} />

        <Route
          path="/wnba_dashboard.html"
          element={<WnbaDashboard />}
        />

        <Route
          path="/soccer_dashboard.html"
          element={<SoccerDashboard />}
        />

        <Route
          path="/live_scores.html"
          element={<LiveScores />}
        />

        <Route
          path="/final_scores.html"
          element={<FinalScores />}
        />

        <Route path="/nfl_dashboard.html" element={<NflDashboard />} />
        <Route path="/ncaaf_dashboard.html" element={<CfbDashboard />} />
        <Route path="/news.html" element={<News />} />
        <Route path="/news" element={<News />} />
        <Route path="/injury_tracker.html" element={<InjuryTracker />} />
        <Route path="/transactions.html" element={<Transactions />} />

        <Route path="/teams.html" element={<Teams />} />
        <Route path="/players.html" element={<Players />} />
        <Route path="/standings.html" element={<Standings />} />

        <Route path="/the_picks.html" element={<ThePicks />} />
        <Route path="/prop_engine.html" element={<PropEngine />} />
        <Route path="/props_nfl.html" element={<PropsNfl />} />
        <Route path="/kelly_calculator.html" element={<KellyCalculator />} />

        <Route path="/bet_history.html" element={<BetHistory />} />
        <Route path="/bet_history_daily.html" element={<BetHistoryDaily />} />
        <Route path="/model_validation.html" element={<ModelValidation />} />
        <Route path="/manual_data.html" element={<ManualData />} />
        <Route path="/manual_venue_data.html" element={<ManualVenueData />} />
        <Route path="/pipeline_health.html" element={<PipelineHealth />} />
        <Route path="/football_dashboard.html" element={<FootballMaster />} />
        <Route path="/props_dashboard.html" element={<PropsMaster />} />
        <Route path="/ncaab_dashboard.html" element={<NcaamDashboard />} />
        <Route path="/mat.html" element={<MatDashboard />} />
        <Route path="/about.html" element={<About />} />
        <Route path="/accessibility.html" element={<Accessibility />} />
        <Route path="/disclaimer.html" element={<Disclaimer />} />
        <Route path="/faq.html" element={<Faq />} />
        <Route path="/methodology.html" element={<Methodology />} />
        <Route path="/privacy.html" element={<Privacy />} />
        <Route path="/responsible_gambling.html" element={<ResponsibleGambling />} />
        <Route path="/terms.html" element={<Terms />} />

      </Routes>
    </SiteShell>
  );
}




















