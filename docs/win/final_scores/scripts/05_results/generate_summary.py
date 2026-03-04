# docs/win/final_scores/scripts/05_results/generate_summary.py
import pandas as pd
import glob
import os

def generate_reports():
    # Define the sports and their specific configurations
    sports_config = [
        {"name": "nhl", "suffix": "NHL", "markets": ['moneyline', 'total', 'puck_line']},
        {"name": "nba", "suffix": "NBA", "markets": ['moneyline', 'total', 'spread']},
        {"name": "ncaab", "suffix": "NCAAB", "markets": ['moneyline', 'total', 'spread']}
    ]

    for sport in sports_config:
        sport_name = sport["name"]
        suffix = sport["suffix"]
        required_markets = sport["markets"]

        results_dir = f"docs/win/final_scores/results/{sport_name}/graded"
        output_base = f"docs/win/final_scores/results/{sport_name}"
        
        # Output file paths
        team_output = os.path.join(output_base, "summary_tally.csv")
        market_output = os.path.join(output_base, "market_tally.csv")
        txt_output = os.path.join(output_base, "performance_report.txt")
        txt_output_xtra = os.path.join(output_base, "performance_report-xtra.txt")
        
        os.makedirs(output_base, exist_ok=True)
        
        # Find graded results files
        files = glob.glob(os.path.join(results_dir, f"*_results_{suffix}.csv"))
        if not files:
            print(f"No files found for {suffix} in {results_dir}")
            continue

        # Load all data for this sport
        all_data = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)

        # --- DEDUPLICATION STEP ---
        all_data = all_data.drop_duplicates(subset=['game_date', 'away_team', 'home_team', 'market_type', 'bet_side', 'line'])

        # --- REPORT 1: TEAM TALLY (CSV) ---
        away_stats = all_data[['away_team', 'market_type', 'bet_result']].rename(columns={'away_team': 'team'})
        home_stats = all_data[['home_team', 'market_type', 'bet_result']].rename(columns={'home_team': 'team'})
        combined_teams = pd.concat([away_stats, home_stats], ignore_index=True)
        
        team_tally = combined_teams.groupby(['team', 'market_type', 'bet_result']).size().unstack(fill_value=0)
        for col in ['Win', 'Loss', 'Push']:
            if col not in team_tally.columns: team_tally[col] = 0
        
        team_tally['Total'] = team_tally['Win'] + team_tally['Loss'] + team_tally['Push']
        team_tally['Win_Pct'] = (team_tally['Win'] / team_tally['Total']).fillna(0).round(3)
        team_tally = team_tally[['Win', 'Loss', 'Push', 'Total', 'Win_Pct']].reset_index()
        team_tally.to_csv(team_output, index=False)

        # --- REPORT 2: MARKET TALLY (CSV) ---
        market_tally = all_data.groupby(['market_type', 'bet_result']).size().unstack(fill_value=0)
        for m in required_markets:
            if m not in market_tally.index: market_tally.loc[m] = 0
        for col in ['Win', 'Loss', 'Push']:
            if col not in market_tally.columns: market_tally[col] = 0
                
        market_tally['Total'] = market_tally['Win'] + market_tally['Loss'] + market_tally['Push']
        market_tally['Win_Pct'] = (market_tally['Win'] / market_tally['Total']).fillna(0).round(3)
        
        existing_markets = [m for m in required_markets if m in market_tally.index]
        market_tally = market_tally.loc[existing_markets, ['Win', 'Loss', 'Push', 'Total', 'Win_Pct']].reset_index()
        market_tally.to_csv(market_output, index=False)

        # --- REPORT 3: PERFORMANCE LOG (TXT) ---
        with open(txt_output, "w") as f:
            f.write(f"=== {suffix.upper()} DETAILED PERFORMANCE LOG ===\n")
            f.write(f"Generated on: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            for market in required_markets:
                market_data = all_data[all_data['market_type'] == market]
                
                f.write(f"--- MARKET: {market.upper()} ---\n")
                if market_data.empty:
                    f.write("No recorded bets for this market.\n\n")
                    continue

                for _, row in market_data.sort_values('game_date', ascending=False).iterrows():
                    res = str(row['bet_result']).upper().ljust(5)
                    date = row['game_date']
                    matchup = f"{row['away_team']} @ {row['home_team']}"
                    details = f"Side: {row['bet_side']} ({row['line']})"
                    score = f"Score: {row['away_score']}-{row['home_score']}"
                    
                    f.write(f"[{res}] {date} | {matchup.ljust(45)} | {details.ljust(20)} | {score}\n")

                stats_rows = market_tally[market_tally['market_type'] == market]
                if not stats_rows.empty:
                    stats = stats_rows.iloc[0]
                    f.write(f"\n{market.upper()} SUMMARY: {stats['Win']}W - {stats['Loss']}L - {stats['Push']}P")
                    f.write(f" | Win Rate: {stats['Win_Pct']*100:.1f}%\n")
                f.write("-" * 90 + "\n\n")

        # ---------------------------------------------------------------------
        # --- REPORT 4: EXTRA PERFORMANCE ANALYTICS ---
        # ---------------------------------------------------------------------

        with open(txt_output_xtra, "w") as f:

            f.write(f"=== {suffix.upper()} PERFORMANCE REPORT (EXTRA) ===\n")
            f.write(f"Generated on: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            wins = (all_data['bet_result'] == 'Win').sum()
            losses = (all_data['bet_result'] == 'Loss').sum()
            pushes = (all_data['bet_result'] == 'Push').sum()
            total = wins + losses + pushes
            win_rate = (wins / total) if total else 0

            f.write("OVERALL RECORD\n")
            f.write(f"Wins: {wins}\n")
            f.write(f"Losses: {losses}\n")
            f.write(f"Pushes: {pushes}\n")
            f.write(f"Win Rate: {win_rate*100:.2f}%\n\n")

            # -------------------------------------------------------------
            # EDGE DIAGNOSTIC (NEW)
            # -------------------------------------------------------------

            f.write("EDGE DIAGNOSTIC\n")

            def extract_edge(row):
                try:
                    if row['bet_side'] == 'home':
                        return float(row.get('home_edge_decimal', 0))
                    if row['bet_side'] == 'away':
                        return float(row.get('away_edge_decimal', 0))
                    if row['bet_side'] == 'over':
                        return float(row.get('over_edge_decimal', 0))
                    if row['bet_side'] == 'under':
                        return float(row.get('under_edge_decimal', 0))
                except:
                    return None
                return None

            all_data['edge_used'] = all_data.apply(extract_edge, axis=1)

            win_edges = all_data[all_data['bet_result'] == 'Win']['edge_used'].dropna()
            loss_edges = all_data[all_data['bet_result'] == 'Loss']['edge_used'].dropna()
            push_edges = all_data[all_data['bet_result'] == 'Push']['edge_used'].dropna()

            win_avg = win_edges.mean() if not win_edges.empty else 0
            loss_avg = loss_edges.mean() if not loss_edges.empty else 0
            push_avg = push_edges.mean() if not push_edges.empty else 0

            f.write(f"Average edge (wins): {round(win_avg,4)}\n")
            f.write(f"Average edge (losses): {round(loss_avg,4)}\n")
            f.write(f"Average edge (pushes): {round(push_avg,4)}\n")

            if win_avg > loss_avg:
                f.write("Edge signal direction: CORRECT (wins have higher edges)\n\n")
            else:
                f.write("Edge signal direction: INVERTED (losses have higher edges)\n\n")

            # Home / Away split
            home_data = all_data[all_data['bet_side'] == 'home']
            away_data = all_data[all_data['bet_side'] == 'away']

            def record(df):
                w = (df['bet_result'] == 'Win').sum()
                l = (df['bet_result'] == 'Loss').sum()
                p = (df['bet_result'] == 'Push').sum()
                return w, l, p

            hw, hl, hp = record(home_data)
            aw, al, ap = record(away_data)

            f.write("HOME / AWAY SPLIT\n")
            f.write(f"Home bets: {hw}W - {hl}L - {hp}P\n")
            f.write(f"Away bets: {aw}W - {al}L - {ap}P\n\n")

            totals = all_data[all_data['market_type'] == 'total']
            overs = totals[totals['bet_side'] == 'over']
            unders = totals[totals['bet_side'] == 'under']

            ow, ol, op = record(overs)
            uw, ul, up = record(unders)

            f.write("OVER / UNDER SPLIT\n")
            f.write(f"Overs: {ow}W - {ol}L - {op}P\n")
            f.write(f"Unders: {uw}W - {ul}L - {up}P\n\n")

            f.write("="*90 + "\n\n")

            for market in required_markets:

                f.write(f"--- MARKET: {market.upper()} ---\n")

                mdata = all_data[all_data['market_type'] == market]

                if mdata.empty:
                    f.write("No bets recorded.\n\n")
                    continue

                biggest_win = None
                biggest_loss = None

                for _, row in mdata.iterrows():

                    away = float(row['away_score'])
                    home = float(row['home_score'])

                    margin = None

                    if market == "moneyline":
                        margin = abs(away - home)

                    elif market in ["spread", "puck_line"]:
                        line = float(row['line'])
                        if row['bet_side'] == 'away':
                            margin = (away + line) - home
                        else:
                            margin = (home + line) - away

                    elif market == "total":
                        line = float(row['line'])
                        total_score = away + home
                        margin = total_score - line

                    if margin is not None:
                        if biggest_win is None or margin > biggest_win:
                            biggest_win = margin
                        if biggest_loss is None or margin < biggest_loss:
                            biggest_loss = margin

                mw, ml, mp = record(mdata)

                f.write(f"Record: {mw}W - {ml}L - {mp}P\n")

                if biggest_win is not None:
                    f.write(f"Largest Positive Margin: {round(biggest_win,2)}\n")

                if biggest_loss is not None:
                    f.write(f"Largest Negative Margin: {round(biggest_loss,2)}\n")

                f.write("\n")

        print(f"Reports saved for {suffix} to {output_base}/")

if __name__ == "__main__":
    generate_reports()
