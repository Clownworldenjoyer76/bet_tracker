// apps.js
// Create XLSX from pasted tabular data
// DOES NOT modify time or data

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

            // Split pasted data exactly like Excel / Sheets
            const rows = rawData
                .split("\n")
                .map(r => r.replace(/\r/g, "").trim())
                .filter(Boolean)
                .map(r => r.split("\t"));

            if (rows.length === 0) {
                throw new Error("No data detected");
            }

            // Build XLSX
            const wb = XLSX.utils.book_new();
            const ws = XLSX.utils.aoa_to_sheet(rows);
            XLSX.utils.book_append_sheet(wb, ws, "data");

            const arrayBuffer = XLSX.write(wb, {
                bookType: "xlsx",
                type: "array"
            });

            const filename = `win_prob_${league}_${date}.xlsx`;

            await commitToGitHub(token, filename, arrayBuffer);

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

async function commitToGitHub(token, filename, arrayBuffer) {
    const owner = "Clownworldenjoyer76";
    const repo = "bet_tracker";
    const path = `docs/win/${filename}`;

    const bytes = new Uint8Array(arrayBuffer);
    let binary = "";
    for (let i = 0; i < bytes.length; i++) {
        binary += String.fromCharCode(bytes[i]);
    }

    const content = btoa(binary);

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
                content
            })
        }
    );

    if (!res.ok) {
        const text = await res.text();
        throw new Error(text);
    }
}
