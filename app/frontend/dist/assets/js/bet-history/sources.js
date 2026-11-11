/*
  Toggle leagues here.

  Use enabled:false to deactivate a league without deleting its path.
  Example: Soccer is currently disabled.

  NHL graded history is date-based. assets/js/bet-history/app.js must support
  datePattern sources for this file to load NHL history.
*/

var SOURCES = [
  {
    url: BASE + 'frontend/data/mlb/final/MLB_final.csv',
    label: 'MLB',
    enabled: true
  },
  {
    url: BASE + 'frontend/data/basketball/basketball_final.csv',
    label: 'BASKETBALL',
    enabled: true
  },
  {
    url: BASE + 'frontend/data/nhl/nhl_final.csv',
    label: 'NHL',
    enabled: true
  },
  {
    url: BASE + 'frontend/data/soccer/soccer_final.csv',
    label: 'SOCCER',
    enabled: true
  },
  {
    indexUrl: 'https://api.github.com/repos/' + REPO + '/contents/frontend/data/ufc/graded?ref=' + BRANCH,
    indexItemToUrl: function(item) {
      if (!item || item.type !== 'file') return '';
      if (!/^\d{4}_\d{2}_\d{2}_graded_ufc\.csv$/i.test(item.name || '')) return '';
      return item.download_url || '';
    },
    label: 'UFC',
    enabled: true
  }
];
