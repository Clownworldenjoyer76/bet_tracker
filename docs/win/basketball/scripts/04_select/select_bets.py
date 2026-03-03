# =========================
# MONEYLINE (NBA UPDATED)
# =========================
if market == "moneyline" and league == "NBA":
    for side in ["home", "away"]:
        edge_dec = row.get(f"{side}_edge_decimal")
        win_prob = row.get(f"{side}_prob")
        american_odds = row.get(f"{side}_juice_odds")

        if pd.isna(edge_dec) or pd.isna(win_prob) or pd.isna(american_odds):
            continue

        odds = pd.to_numeric(american_odds, errors="coerce")

        # Apply New NBA Bands
        if 100 <= odds <= 149:
            if not (edge_dec >= 0.05 and win_prob >= 0.42): continue
        elif 150 <= odds <= 199:
            if not (edge_dec >= 0.06 and win_prob >= 0.40): continue
        elif 200 <= odds <= 299:
            if not (edge_dec >= 0.07 and win_prob >= 0.35): continue
        elif odds >= 300:
            continue # SKIP ENTIRELY
        elif -149 <= odds <= -100:
            if not (edge_dec >= 0.05 and win_prob >= 0.58): continue
        elif -249 <= odds <= -150:
            if not (edge_dec >= 0.06 and win_prob >= 0.62): continue
        elif odds <= -250:
            if not (edge_dec >= 0.08 and win_prob >= 0.80): continue
        else:
            continue

        selections.append({
            "game_date": game_date, "league": league, "away_team": away_team,
            "home_team": home_team, "market_type": "moneyline", "bet_side": side,
            "line": "", "game_id": game_id, "market": market,
            "take_bet": f"{side}_ml", "take_odds": american_odds, "take_team": side,
            "value": win_prob, "take_bet_edge_decimal": edge_dec, 
            "take_bet_edge_pct": row.get(f"{side}_edge_pct")
        })

# =========================
# TOTAL (NBA UPDATED)
# =========================
elif market == "total" and league == "NBA":
    for side in ["over", "under"]:
        edge_dec = row.get(f"{side}_edge_decimal")
        edge_pct = row.get(f"{side}_edge_pct")
        odds = row.get(f"total_{side}_juice_odds")

        # New NBA Total Threshold: 10% (0.10)
        if pd.notna(edge_dec) and edge_dec >= 0.10 and valid_total_odds(odds):
            selections.append({
                "game_date": game_date, "league": league, "away_team": away_team,
                "home_team": home_team, "market_type": "total", "bet_side": side,
                "line": row.get("total"), "game_id": game_id, "market": market,
                "take_bet": f"{side}_bet", "take_odds": odds, "take_team": side,
                "value": row.get("total"), "take_bet_edge_decimal": edge_dec, 
                "take_bet_edge_pct": edge_pct
            })
