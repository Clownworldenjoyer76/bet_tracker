import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { resolve } from "node:path";

const rootDir = import.meta.dirname;

export default defineConfig({
  plugins: [react()],
  base: "./",
  server: {
    fs: {
      allow: [
        rootDir,
        resolve(rootDir, "../app/frontend/src"),
      ],
    },
  },
  build: {
    outDir: "react-dist",
    emptyOutDir: true,
    rolldownOptions: {
      input: {
        main: resolve(rootDir, "index.html"),
        gamesToday: resolve(rootDir, "games_today.html"),
        liveScores: resolve(rootDir, "live_scores.html"),
        finalScores: resolve(rootDir, "final_scores.html"),
        news: resolve(rootDir, "news.html"),
        injuryTracker: resolve(rootDir, "injury_tracker.html"),
        transactions: resolve(rootDir, "transactions.html"),
        teams: resolve(rootDir, "teams.html"),
        players: resolve(rootDir, "players.html"),
        standings: resolve(rootDir, "standings.html"),
        thePicks: resolve(rootDir, "the_picks.html"),
        propEngine: resolve(rootDir, "prop_engine.html"),
        propsNfl: resolve(rootDir, "props_nfl.html"),
        kellyCalculator: resolve(rootDir, "kelly_calculator.html"),
        betHistory: resolve(rootDir, "bet_history.html"),
        betHistoryDaily: resolve(rootDir, "bet_history_daily.html"),
        mlbDashboard: resolve(rootDir, "mlb_dashboard.html"),
        baseballDashboard: resolve(rootDir, "baseball_dashboard.html"),
        modelValidation: resolve(rootDir, "model_validation.html"),
        account: resolve(rootDir, "account.html"),
        login: resolve(rootDir, "login.html"),
        register: resolve(rootDir, "register.html"),
        contact: resolve(rootDir, "contact.html"),
        passwordReset: resolve(rootDir, "password_reset.html"),
        passwordResetDone: resolve(rootDir, "password_reset_done.html"),
        passwordResetComplete: resolve(rootDir, "password_reset_complete.html"),
        manualData: resolve(rootDir, "manual_data.html"),
        manualVenueData: resolve(rootDir, "manual_venue_data.html"),
        pipelineHealth: resolve(rootDir, "pipeline_health.html"),
        nbaDashboard: resolve(rootDir, "nba_dashboard.html"),
        ncaamDashboard: resolve(rootDir, "ncaam_dashboard.html"),
        basketballDashboard: resolve(rootDir, "basketball_dashboard.html"),
        wnbaDashboard: resolve(rootDir, "wnba_dashboard.html"),
        nflDashboard: resolve(rootDir, "nfl_dashboard.html"),
        ncaafDashboard: resolve(rootDir, "ncaaf_dashboard.html"),
        ufcDashboard: resolve(rootDir, "ufc_dashboard.html"),
        nhlDashboard: resolve(rootDir, "nhl_dashboard.html"),
        soccerDashboard: resolve(rootDir, "soccer_dashboard.html"),
        footballDashboard: resolve(rootDir, "football_dashboard.html"),
        propsDashboard: resolve(rootDir, "props_dashboard.html"),
        ncaabDashboard: resolve(rootDir, "ncaab_dashboard.html"),
        mat: resolve(rootDir, "mat.html"),
        about: resolve(rootDir, "about.html"),
        accessibility: resolve(rootDir, "accessibility.html"),
        disclaimer: resolve(rootDir, "disclaimer.html"),
        faq: resolve(rootDir, "faq.html"),
        methodology: resolve(rootDir, "methodology.html"),
        privacy: resolve(rootDir, "privacy.html"),
        responsibleGambling: resolve(rootDir, "responsible_gambling.html"),
        terms: resolve(rootDir, "terms.html"),
      },
    },
  },
});













