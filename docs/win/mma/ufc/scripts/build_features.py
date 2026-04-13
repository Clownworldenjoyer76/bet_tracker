import pandas as pd
import json
import numpy as np
from datetime import datetime

# Load data
df = pd.read_parquet("ufc_master_clean.parquet")
with open("fighter_attributes.json") as f:
    attrs = json.load(f)

# Parse DOB
def parse_dob(name):
    if name in attrs and "dob" in attrs[name]:
        try:
            return pd.to_datetime(attrs[name]["dob"])
        except:
            return None
    return None

def parse_height_inches(name):
    if name not in attrs or "height" not in attrs[name]:
        return None
    h = attrs[name]["height"]
    try:
        parts = h.replace('"', '').split("'")
        return int(parts[0]) * 12 + int(parts[1].strip())
    except:
        return None

def parse_reach(name):
    if name not in attrs or "reach" not in attrs[name]:
        return None
    try:
        return float(attrs[name]["reach"].replace('"', '').strip())
    except:
        return None

def parse_stance(name):
    if name not in attrs or "stance" not in attrs[name]:
        return None
    return attrs[name]["stance"]

# Sort by date to ensure correct rolling calculations
df = df.sort_values("match_date").reset_index(drop=True)

# Build fight history per fighter up to each fight
# We'll compute stats for each fighter using all their prior fights

def build_fighter_history(df):
    """Returns a dict: fighter -> list of (date, win) sorted by date"""
    history = {}
    for _, row in df.iterrows():
        date = row["match_date"]
        for fighter, result in [(row["fighter_1"], row["result_fighter_1"]),
                                 (row["fighter_2"], row["result_fighter_2"])]:
            if fighter not in history:
                history[fighter] = []
            history[fighter].append((date, 1 if result == "Win" else 0))
    # Sort each fighter's history by date
    for f in history:
        history[f] = sorted(history[f], key=lambda x: x[0])
    return history

history = build_fighter_history(df)

def get_stats(fighter, fight_date, history, n_last=5):
    """Get rolling stats for a fighter BEFORE the given fight date"""
    fights = [(d, w) for d, w in history.get(fighter, []) if d < fight_date]
    
    if len(fights) == 0:
        return {
            "win_rate_all": None,
            "win_rate_last5": None,
            "streak": 0,
            "experience": 0,
            "days_since_last": None,
        }
    
    wins = [w for _, w in fights]
    dates = [d for d, _ in fights]
    
    win_rate_all = np.mean(wins)
    win_rate_last5 = np.mean(wins[-n_last:]) if len(wins) >= 1 else None
    
    # Streak: count consecutive same results from most recent
    streak = 0
    last = wins[-1]
    for w in reversed(wins):
        if w == last:
            streak += 1
        else:
            break
    streak = streak if last == 1 else -streak  # positive=win streak, negative=loss streak
    
    experience = len(fights)
    days_since_last = (fight_date - dates[-1]).days if dates else None
    
    return {
        "win_rate_all": win_rate_all,
        "win_rate_last5": win_rate_last5,
        "streak": streak,
        "experience": experience,
        "days_since_last": days_since_last,
    }

def get_sos(fighter, fight_date, history, df):
    """Strength of schedule: avg win rate of past opponents"""
    # Get past opponents
    past = []
    for _, row in df.iterrows():
        if row["match_date"] >= fight_date:
            continue
        if row["fighter_1"] == fighter:
            past.append(row["fighter_2"])
        elif row["fighter_2"] == fighter:
            past.append(row["fighter_1"])
    
    if not past:
        return None
    
    opp_win_rates = []
    for opp in past:
        opp_fights = [(d, w) for d, w in history.get(opp, []) if d < fight_date]
        if opp_fights:
            opp_win_rates.append(np.mean([w for _, w in opp_fights]))
    
    return np.mean(opp_win_rates) if opp_win_rates else None

def implied_prob(moneyline):
    """Convert moneyline to implied probability"""
    try:
        ml = float(str(moneyline).replace("+", ""))
        if ml > 0:
            return 100 / (ml + 100)
        else:
            return abs(ml) / (abs(ml) + 100)
    except:
        return None

print("Building features... (this may take a few minutes)")

rows = []
for idx, row in df.iterrows():
    if idx % 200 == 0:
        print(f"  Processing row {idx}/{len(df)}")
    
    f1, f2 = row["fighter_1"], row["fighter_2"]
    date = row["match_date"]
    
    s1 = get_stats(f1, date, history)
    s2 = get_stats(f2, date, history)
    
    sos1 = get_sos(f1, date, history, df)
    sos2 = get_sos(f2, date, history, df)
    
    ip1_raw = implied_prob(row["moneyline_fighter_1"])
    ip2_raw = implied_prob(row["moneyline_fighter_2"])
    
    # Remove vig - normalize so they sum to 1
    if ip1_raw and ip2_raw:
        total = ip1_raw + ip2_raw
        ip1 = ip1_raw / total
        ip2 = ip2_raw / total
    else:
        ip1 = ip2 = None
    
    # Physical attributes
    age1 = (date - parse_dob(f1)).days / 365.25 if parse_dob(f1) else None
    age2 = (date - parse_dob(f2)).days / 365.25 if parse_dob(f2) else None
    reach1 = parse_reach(f1)
    reach2 = parse_reach(f2)
    height1 = parse_height_inches(f1)
    height2 = parse_height_inches(f2)
    stance1 = parse_stance(f1)
    stance2 = parse_stance(f2)
    
    result = 1 if row["result_fighter_1"] == "Win" else 0
    
    feature_row = {
        # Identifiers
        "match_date": date,
        "fighter_1": f1,
        "fighter_2": f2,
        "result": result,
        
        # Raw sportsbook
        "moneyline_f1": row["moneyline_fighter_1"],
        "moneyline_f2": row["moneyline_fighter_2"],
        "implied_prob_f1": ip1,
        "implied_prob_f2": ip2,
        "win_prob_f1": row["win_prob_1"],  # your existing model prob
        
        # Fighter 1 stats
        "f1_win_rate_all": s1["win_rate_all"],
        "f1_win_rate_last5": s1["win_rate_last5"],
        "f1_streak": s1["streak"],
        "f1_experience": s1["experience"],
        "f1_days_since_last": s1["days_since_last"],
        "f1_sos": sos1,
        "f1_age": age1,
        "f1_reach": reach1,
        "f1_height": height1,
        "f1_stance": stance1,
        
        # Fighter 2 stats
        "f2_win_rate_all": s2["win_rate_all"],
        "f2_win_rate_last5": s2["win_rate_last5"],
        "f2_streak": s2["streak"],
        "f2_experience": s2["experience"],
        "f2_days_since_last": s2["days_since_last"],
        "f2_sos": sos2,
        "f2_age": age2,
        "f2_reach": reach2,
        "f2_height": height2,
        "f2_stance": stance2,
        
        # Differential features (f1 - f2)
        "diff_win_rate_all": (s1["win_rate_all"] or 0) - (s2["win_rate_all"] or 0),
        "diff_win_rate_last5": (s1["win_rate_last5"] or 0) - (s2["win_rate_last5"] or 0),
        "diff_streak": s1["streak"] - s2["streak"],
        "diff_experience": s1["experience"] - s2["experience"],
        "diff_days_since_last": (s1["days_since_last"] or 0) - (s2["days_since_last"] or 0),
        "diff_sos": (sos1 or 0) - (sos2 or 0),
        "diff_age": (age1 or 0) - (age2 or 0),
        "diff_reach": (reach1 or 0) - (reach2 or 0),
        "diff_height": (height1 or 0) - (height2 or 0),
    }
    rows.append(feature_row)

features = pd.DataFrame(rows)

# Add mirror rows (fighter 2 perspective) to remove position bias
mirror = features.copy()
mirror["fighter_1"] = features["fighter_2"]
mirror["fighter_2"] = features["fighter_1"]
mirror["result"] = 1 - features["result"]
mirror["implied_prob_f1"] = features["implied_prob_f2"]
mirror["implied_prob_f2"] = features["implied_prob_f1"]
mirror["moneyline_f1"] = features["moneyline_f2"]
mirror["moneyline_f2"] = features["moneyline_f1"]
mirror["win_prob_f1"] = 1 - features["win_prob_f1"].astype(float)

for col in ["win_rate_all","win_rate_last5","streak","experience","days_since_last","sos","age","reach","height","stance"]:
    mirror[f"f1_{col}"] = features[f"f2_{col}"]
    mirror[f"f2_{col}"] = features[f"f1_{col}"]

for col in ["win_rate_all","win_rate_last5","streak","experience","days_since_last","sos","age","reach","height"]:
    mirror[f"diff_{col}"] = -features[f"diff_{col}"]

full = pd.concat([features, mirror], ignore_index=True)
full = full.sort_values("match_date").reset_index(drop=True)

print(f"\nFeature matrix shape: {full.shape}")
print(f"Columns: {list(full.columns)}")
print(f"Missing values per column:\n{full.isnull().sum()[full.isnull().sum() > 0]}")

full.to_parquet("ufc_features.parquet", index=False)
print("\nSaved to ufc_features.parquet")
