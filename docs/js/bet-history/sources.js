/*
  Toggle leagues here.

  Use enabled:false to deactivate a league without deleting its path.
  Example: Soccer is currently disabled.
*/

var SOURCES = [
  {
    url: BASE + 'docs/win/baseball/05_final_scores/results/graded/MLB_final.csv',
    label: 'MLB',
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
    url: BASE + 'docs/win/final_scores/results/nhl/graded/NHL_final.csv',
    label: 'NHL',
    enabled: true
  },
  {
    url: BASE + 'docs/win/soccer/05_final_scores/results/graded/SOCCER_final.csv',
    label: 'SOCCER',
    enabled: false
  }
];
