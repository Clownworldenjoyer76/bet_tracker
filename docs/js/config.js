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
      `win/basketball/04_select/${date}_basketball_NBA_moneyline.csv`,
      `win/basketball/04_select/${date}_basketball_NBA_spread.csv`,
      `win/basketball/04_select/${date}_basketball_NBA_total.csv`
    ],
    predFile:(date)=>`win/basketball/00_intake/predictions/basketball_NBA_${date}.csv`,
    bookFile:(date)=>`win/basketball/00_intake/sportsbook/basketball_NBA_${date}.csv`
  },

  NCAAB:{
    sport:"basketball",
    isHockey:false,
    selectFiles:(date)=>[
      `win/basketball/04_select/${date}_basketball_NCAAB_moneyline.csv`,
      `win/basketball/04_select/${date}_basketball_NCAAB_spread.csv`,
      `win/basketball/04_select/${date}_basketball_NCAAB_total.csv`
    ],
    predFile:(date)=>`win/basketball/00_intake/predictions/basketball_NCAAB_${date}.csv`,
    bookFile:(date)=>`win/basketball/00_intake/sportsbook/basketball_NCAAB_${date}.csv`
  }

};
