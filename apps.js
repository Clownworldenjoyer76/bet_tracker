// apps.js
// Frontend CSV writer
// NO XLSX
// NO external libraries
// NO time modification
// Writes EXACTLY what is pasted, but as a real CSV

document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("win-prob-form");
    if (!form) return;

    form.addEventListener("submit", async (e) => {
        e.preventDefault();

        try {
            const league = document.getElementById("league").value.trim();
            const date = document.getElementById("date").value.trim();
            const rawData = document.getElementById("raw-data").value.trim();
            const token = document.getElementById("github-token").value.trim();

            if (!league || !date || !rawData || !token) {
                throw new Error("Missing required field");
            }

            // Expect pasted data in TABULAR form (like Google Sheets)
            // Each row = one game
            // Columns expected (TAB-separated):
            // date | time | team_a | team_b | win_probability_a | win_probability_b

            const lines = rawData
                .split("\n")
                .map(l => l.replace(/\r/g, "").trim())
                .filter(Boolean);

            if (lines.length === 0) {
                throw new Error("No data detected");
            }

            const header = [
                "date",
                "time",
                "team_a",
                "team_b",
                "win_probability_a",
                "win_probability_b",
                "league"
            ];

            let csv = header.join(",") + "\n";

            for (const line of lines) {
                const cols = line.split("\t");

                if (cols.length < 6) {
                    throw new Error("Each row must have at least 6 tab-separated columns");
                }

                const [
                    rowDate,
                    rowTime,
                    teamA,
                    teamB,
                    probA,
                    probB
                ] = cols;

                const row = [
                    rowDate,
                    rowTime,
                    teamA,
                    teamB,
                    probA,
                    probB,
                    league
                ].map(v => `"${String(v).replace(/"/g, '""')}"`);

                csv += row.join(",") + "\n";
            }

            const filename = `win_prob_${league}_${date}.csv`;

            await commitToGitHub(token, filename, csv);

            alert(
                "SUCCESS\n\n" +
                `Saved to docs/win/${filename}`
            );

        } catch (err) {
            alert(
                "FAILED\n\n" +
                err.message
            );
        }
    });
});

async function commitToGitHub(token, filename, content) {
    const owner = "Clownworldenjoyer76";
    const repo = "bet_tracker";
    const path = `docs/win/${filename}`;

    const encoded = btoa(
        unescape(encodeURIComponent(content))
    );

    const response = await fetch(
        `https://api.github.com/repos/${owner}/${repo}/contents/${path}`,
        {
            method: "PUT",
            headers: {
                "Authorization": `token ${token}`,
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                message: `Add ${filename}`,
                content: encoded
            })
        }
    );

    if (!response.ok) {
        const text = await response.text();
        throw new Error(text);
    }
}
