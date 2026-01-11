// app.js
// Core client-side logic for Win Probability CSV Generator

document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("win-prob-form");

    form.addEventListener("submit", async (e) => {
        e.preventDefault();

        try {
            const league = getRequiredValue("league");
            const date = getRequiredValue("date");
            const rawData = getRequiredValue("raw-data");
            const token = getRequiredValue("github-token");

            const games = parseRawGameData(rawData);
            const rows = buildRows(games, league, date);
            const csv = buildCSV(rows);

            const filename = `win_prob_${league}_${date}.csv`;
            await commitToGitHub({
                token,
                filename,
                content: csv
            });

            alert(`Success: ${filename} committed to GitHub.`);
        } catch (err) {
            alert(`ERROR: ${err.message}`);
        }
    });
});

/* =========================
   Helpers
   ========================= */

function getRequiredValue(id) {
    const el = document.getElementById(id);
    if (!el || !el.value.trim()) {
        throw new Error(`Missing required field: ${id}`);
    }
    return el.value.trim();
}

/* =========================
   Parsing & Normalization
   ========================= */

function parseRawGameData(raw) {
    const lines = raw
        .split("\n")
        .map(l => l.trim())
        .filter(l => l.length > 0);

    if (lines.length < 4) {
        throw new Error("Raw data does not contain enough lines to form a game.");
    }

    const games = [];
    let i = 0;

    while (i < lines.length) {
        const time = extractTime(lines[i]);
        if (!time) {
            throw new Error(`Expected time on line ${i + 1}: "${lines[i]}"`);
        }
        i++;

        if (i + 3 > lines.length) {
            throw new Error(`Incomplete game block starting at time ${time}`);
        }

        const teamA = parseTeamLine(lines[i]);
        const teamB = parseTeamLine(lines[i + 1]);

        games.push({
            time,
            teamA,
            teamB
        });

        i += 2;
    }

    return games;
}

function extractTime(line) {
    // Accepts formats like "02:00 PM", "2:00 PM", "14:30"
    const timeRegex = /^(\d{1,2}:\d{2})(\s?[AP]M)?$/i;
    return timeRegex.test(line) ? line : null;
}

function parseTeamLine(line) {
    // Expect: "Team Name (10-5) 61.5%" or "Team Name 0.615"
    const parts = line.split(/\s+/);
    const probRaw = parts[parts.length - 1];

    const probability = normalizeProbability(probRaw);
    if (probability < 0 || probability > 1) {
        throw new Error(`Invalid win probability: "${probRaw}"`);
    }

    const teamRaw = line.slice(0, line.lastIndexOf(probRaw)).trim();
    const team = stripRecord(teamRaw);

    if (!team) {
        throw new Error(`Could not parse team name from line: "${line}"`);
    }

    return { team, probability };
}

function normalizeProbability(raw) {
    let p = raw.replace("%", "");
    if (isNaN(p)) {
        throw new Error(`Invalid probability value: "${raw}"`);
    }
    p = Number(p);
    if (p > 1) {
        p = p / 100;
    }
    return p;
}

function stripRecord(team) {
    return team.replace(/\s*\([^)]*\)\s*$/, "").trim();
}

/* =========================
   CSV Construction
   ========================= */

function buildRows(games, league, date) {
    const rows = [];

    games.forEach(game => {
        rows.push({
            date,
            time: game.time,
            team: game.teamA.team,
            opponent: game.teamB.team,
            win_probability: game.teamA.probability,
            league
        });

        rows.push({
            date,
            time: game.time,
            team: game.teamB.team,
            opponent: game.teamA.team,
            win_probability: game.teamB.probability,
            league
        });
    });

    return rows;
}

function buildCSV(rows) {
    const headers = [
        "date",
        "time",
        "team",
        "opponent",
        "win_probability",
        "league"
    ];

    const lines = [headers.join(",")];

    rows.forEach(r => {
        lines.push([
            r.date,
            r.time,
            escapeCSV(r.team),
            escapeCSV(r.opponent),
            r.win_probability,
            r.league
        ].join(","));
    });

    return lines.join("\n");
}

function escapeCSV(value) {
    if (value.includes(",") || value.includes("\"")) {
        return `"${value.replace(/"/g, "\"\"")}"`;
    }
    return value;
}

/* =========================
   GitHub Commit
   ========================= */

async function commitToGitHub({ token, filename, content }) {
    const owner = "<YOUR_GITHUB_USERNAME>";
    const repo = "<YOUR_REPO_NAME>";
    const path = `docs/win/${filename}`;

    const apiUrl = `https://api.github.com/repos/${owner}/${repo}/contents/${path}`;

    const encodedContent = btoa(unescape(encodeURIComponent(content)));

    const response = await fetch(apiUrl, {
        method: "PUT",
        headers: {
            "Authorization": `token ${token}`,
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            message: `Add ${filename}`,
            content: encodedContent
        })
    });

    if (!response.ok) {
        const text = await response.text();
        throw new Error(`GitHub API error: ${text}`);
    }
}
