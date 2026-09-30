/*
  Toggle leagues here.

  Use enabled:false to deactivate a league without deleting its path.
  Example: Soccer is currently disabled.

  NHL graded history is date-based. assets/js/bet-history/app.js must support
  datePattern sources for this file to load NHL history.
*/

var SOURCES = [
  {
    url: BASE + 'docs/win/baseball/mlb/05_final_scores/morning/results/graded/MLB_final.csv',
    label: 'MLB',
    enabled: true
  },
  {
    url: BASE + 'docs/win/baseball/mlb/05_final_scores/results/graded/MLB_final.csv',
    label: 'MLB_LINEUPS',
    enabled: true
  },
  {
    url: BASE + 'docs/win/basketball/05_final_scores/results/nba/graded/NBA_final.csv',
    label: 'NBA',
    enabled: true
  },
  {
    url: BASE + 'docs/win/basketball/05_final_scores/results/ncaam/graded/NCAAM_final.csv',
    label: 'NCAAM',
    enabled: true
  },
  {
    url: BASE + 'docs/win/basketball/05_final_scores/results/wnba/graded/WNBA_final.csv',
    label: 'WNBA',
    enabled: true
  },
  {
    datePattern: function(date) {
      return BASE + 'docs/win/hockey/nhl/05_final_scores/graded/' + date + '_results_NHL.csv';
    },
    startDate: '2025_10_01',
    label: 'NHL',
    enabled: true
  },
  {
    url: BASE + 'docs/win/soccer/05_final_scores/results/graded/SOCCER_final.csv',
    label: 'SOCCER',
    enabled: true
  },
  {
    indexUrl: 'https://api.github.com/repos/' + REPO + '/contents/docs/win/mma/ufc/04_final/graded?ref=' + BRANCH,
    indexItemToUrl: function(item) {
      if (!item || item.type !== 'file') return '';
      if (!/^\d{4}_\d{2}_\d{2}_ufc_graded\.csv$/i.test(item.name || '')) return '';
      return item.download_url || '';
    },
    label: 'UFC',
    enabled: true
  }
];
