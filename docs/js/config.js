window.REPO_CONFIG = {

  leagues: ["NHL","NBA","NCAAB"],

  NHL:{
    sport:"hockey",
    isHockey:true,
    selectFiles:(date)=>[`win/hockey/04_select/${date}_NHL.csv`],
    predFile:(date)=>`win/hockey/00_intake/predictions/hockey_${date}.csv`,
    bookFile:(date)=>`win/hockey/00_intake/sportsbook/hockey_${date}.csv`
  },

  NBA:{
    sport:"basketball",
    isHockey:false,
    selectFiles:(date)=>[
      `win/basketball/04_select/daily_slate/${date}_nba.csv`
    ],
    predFile:(date)=>`win/basketball/00_intake/predictions/basketball_NBA_${date}.csv`,
    bookFile:(date)=>`win/basketball/00_intake/sportsbook/basketball_NBA_${date}.csv`
  },

  NCAAB:{
    sport:"basketball",
    isHockey:false,
    selectFiles:(date)=>[
      `win/basketball/04_select/daily_slate/${date}_ncaab.csv`
    ],
    predFile:(date)=>`win/basketball/00_intake/predictions/basketball_NCAAB_${date}.csv`,
    bookFile:(date)=>`win/basketball/00_intake/sportsbook/basketball_NCAAB_${date}.csv`
  }

};
