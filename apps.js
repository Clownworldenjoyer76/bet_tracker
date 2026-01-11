// apps.js
// Final version: single confirmation popup on submit only

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
                throw new Error("One or more required fields are empty");
            }

            const csvContent = rawData; // placeholder until parsing logic re-added
            const filename = `win_prob_${league}_${date}.csv`;

            await commitToGitHub({
                token,
                filename,
                content: csvContent
            });

            alert(
                "SUCCESS\n\n" +
                "CSV file was saved.\n\n" +
                "Repository: Clownworldenjoyer76/bet_tracker\n" +
                `Path: docs/win/${filename}`
            );

        } catch (err) {
            alert(
                "FAILED\n\n" +
                "No file was saved.\n\n" +
                `Reason:\n${err.message}`
            );
        }
    });
});

/* =========================
   GitHub Commit
   ========================= */

async function commitToGitHub({ token, filename, content }) {
    const owner = "Clownworldenjoyer76";
    const repo = "bet_tracker";
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
        throw new Error(text);
    }
}
