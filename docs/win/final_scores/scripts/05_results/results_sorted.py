# ADD SOCCER PATHS

INPUTS = {
    "NBA": Path("docs/win/final_scores/results/nba/graded/NBA_final.csv"),
    "NCAAB": Path("docs/win/final_scores/results/ncaab/graded/NCAAB_final.csv"),
    "NHL": Path("docs/win/final_scores/results/nhl/graded/NHL_final.csv"),
    "SOCCER": Path("docs/win/final_scores/results/soccer/graded/SOCCER_final.csv"),
}

OUTPUTS = {
    "NBA": Path("docs/win/final_scores/results/nba/graded/NBA_final_sorted.csv"),
    "NCAAB": Path("docs/win/final_scores/results/ncaab/graded/ncaab_final_sorted.csv"),
    "NHL": Path("docs/win/final_scores/results/nhl/graded/nhl_final_sorted.csv"),
    "SOCCER": Path("docs/win/final_scores/results/soccer/graded/soccer_final_sorted.csv"),
}

MARKET_TALLY_INPUTS = {
    "NBA": Path("docs/win/final_scores/results/nba/graded/NBA_final_sorted.csv"),
    "NCAAB": Path("docs/win/final_scores/results/ncaab/graded/ncaab_final_sorted.csv"),
    "NHL": Path("docs/win/final_scores/results/nhl/graded/nhl_final_sorted.csv"),
    "SOCCER": Path("docs/win/final_scores/results/soccer/graded/soccer_final_sorted.csv"),
}

MARKET_TALLY_OUTPUTS = {
    "NBA": Path("docs/win/final_scores/results/market_tally_NBA.csv"),
    "NCAAB": Path("docs/win/final_scores/results/market_tally_NCAAB.csv"),
    "NHL": Path("docs/win/final_scores/results/market_tally_NHL.csv"),
    "SOCCER": Path("docs/win/final_scores/results/market_tally_SOCCER.csv"),
}
