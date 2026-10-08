var SOURCES = [
  {
    url: BASE + 'docs/win/hockey/nhl/05_final_scores/graded/NHL_final.csv',
    label: 'NHL',
    enabled: true
  },
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
    url: BASE + 'docs/win/basketball/05_final_scores/results/wnba/graded/WNBA_final.csv',
    label: 'WNBA',
    enabled: true
  },
  {
    url: BASE + 'docs/win/soccer/05_final_scores/results/graded/SOCCER_final.csv',
    label: 'SOCCER',
    enabled: true
  },
  {
    indexUrl: API_BASE + 'docs/win/football/cfb/04_final_results/graded?ref=' + BRANCH,
    indexItemToUrl: function(item) {
      if (!item || item.type !== 'file') return '';
      if (!/^week_\d+_CFB_graded\.csv$/i.test(item.name || '')) return '';
      return item.download_url || '';
    },
    adapter: 'cfb',
    label: 'CFB',
    enabled: true
  },
  {
    indexUrl: API_BASE + 'docs/win/mma/ufc/04_final/graded?ref=' + BRANCH,
    indexItemToUrl: function(item) {
      if (!item || item.type !== 'file') return '';
      if (!/^\d{4}_\d{2}_\d{2}_ufc_graded\.csv$/i.test(item.name || '')) return '';
      return item.download_url || '';
    },
    adapter: 'ufc',
    label: 'UFC',
    enabled: true
  }
];
