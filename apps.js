// apps.js
// Frontend CSV generator
// One row per game
// NO time changes
// NO inference
// NO external libraries

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

            // Parse pasted tabular data (Sheets / Excel style)
            const rows = rawData
                .split("\n")
                .map(r => r.replace(/\r/g, "").trim())
                .filter(Boolean)
                .map(r => r.split("\t"));

            if (rows.length < 2) {
                throw new Error("Not enough rows detected");
            }

            // Build CSV explicitly
            // Expected column order in pasted data:
            // date | time | team_a | team_b | win_probability_a | win_probability_b
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

            for (const row of rows) {
                if (row.length < 6) {
                    throw new Error("Row missing required columns");
                }

                const [
                    rowDate,
                    rowTime,
                    teamA,
                    teamB,
                    probA,
                    probB
                ] = row;

                csv += [
                    rowDate,
                    rowTime,
                    teamA,
                    teamB,
                    probA,
                    probB,
                    league
                ].map(v => `"${v.replace(/"/g, '""')}"`).join(",") + "\n";
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

    const encodedContent = btoa(
        unescape(encodeURIComponent(content))
    );

    const res = await fetch(
        `https://api.github.com/repos/${owner}/${repo}/contents/${path}`,
        {
            method: "PUT",
            headers: {
                "Authorization": `token ${token}`,
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                message: `Add ${filename}`,
                content: encodedContent
            })
        }
    );

    if (!res.ok) {
        const text = await res.text();
        throw new Error(text);
    }
}
