###############################################################
######################## GAME TRIMMING ########################
###############################################################

def trim_games(df):
    # MAX BETS MODE
    # Do not trim to one bet per game.
    # Pass everything through for diagnostics.

    if df.empty:
        return df

    return df.copy()
