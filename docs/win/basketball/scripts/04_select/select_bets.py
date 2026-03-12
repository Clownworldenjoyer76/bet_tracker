###############################################################
##################### STEP 1 NBA MONEYLINE ####################
###############################################################

def step1_nba_moneyline(row):

    home_edge = f(row.get("home_ml_edge_decimal"))
    away_edge = f(row.get("away_ml_edge_decimal"))

    home_ml = f(row.get("home_dk_moneyline_american"))
    away_ml = f(row.get("away_dk_moneyline_american"))

    if home_edge >= away_edge:
        return True, "PASS STEP 1 NBA ML | max bets", "home", home_ml
    else:
        return True, "PASS STEP 1 NBA ML | max bets", "away", away_ml


###############################################################
##################### STEP 2 NBA SPREAD #######################
###############################################################

def step2_nba_spread(row):

    home_line = f(row.get("home_spread"))
    away_line = f(row.get("away_spread"))

    home_edge = f(row.get("home_spread_edge_decimal"))
    away_edge = f(row.get("away_spread_edge_decimal"))

    if home_edge >= away_edge:
        return True, "PASS STEP 2 NBA SPREAD | max bets", "home", home_line
    else:
        return True, "PASS STEP 2 NBA SPREAD | max bets", "away", away_line


###############################################################
##################### STEP 3 NBA TOTAL ########################
###############################################################

def step3_nba_total(row):

    line = f(row.get("total"))

    over_edge = f(row.get("over_edge_decimal"))
    under_edge = f(row.get("under_edge_decimal"))

    if over_edge >= under_edge:
        return True, "PASS STEP 3 NBA TOTAL | max bets", "over"
    else:
        return True, "PASS STEP 3 NBA TOTAL | max bets", "under"


###############################################################
################### STEP 4 NCAAB MONEYLINE ####################
###############################################################

def step4_ncaab_moneyline(row):

    home_ml = f(row.get("home_dk_moneyline_american"))
    away_ml = f(row.get("away_dk_moneyline_american"))

    home_edge = f(row.get("home_ml_edge_decimal"))
    away_edge = f(row.get("away_ml_edge_decimal"))

    if home_edge >= away_edge:
        return True, "PASS STEP 4 NCAAB ML | max bets", "home", home_ml
    else:
        return True, "PASS STEP 4 NCAAB ML | max bets", "away", away_ml


###############################################################
#################### STEP 5 NCAAB SPREAD ######################
###############################################################

def step5_ncaab_spread(row):

    home_line = f(row.get("home_spread"))
    away_line = f(row.get("away_spread"))

    home_edge = f(row.get("home_spread_edge_decimal"))
    away_edge = f(row.get("away_spread_edge_decimal"))

    if home_edge >= away_edge:
        return True, "PASS STEP 5 NCAAB SPREAD | max bets", "home", home_line
    else:
        return True, "PASS STEP 5 NCAAB SPREAD | max bets", "away", away_line


###############################################################
#################### STEP 6 NCAAB TOTAL #######################
###############################################################

def step6_ncaab_total(row):

    line = f(row.get("total"))

    over_edge = f(row.get("over_edge_decimal"))
    under_edge = f(row.get("under_edge_decimal"))

    if over_edge >= under_edge:
        return True, "PASS STEP 6 NCAAB TOTAL | max bets", "over"
    else:
        return True, "PASS STEP 6 NCAAB TOTAL | max bets", "under"
