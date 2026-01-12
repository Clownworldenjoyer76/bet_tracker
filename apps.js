// apps.js
// XLSX export — NO time modification
// Defensive: hard-fails if XLSX is not loaded

document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("win-prob-form");
    if (!form) return;

    form.addEventListener("submit", async (e) => {
        e.preventDefault();

        try {
            // HARD CHECK — this is what was missing before
            if (typeof XLSX === "undefined") {
                throw new Error(
                    "XLSX library not loaded. Check index.html script order."
                );
            }

            const league = document.getElementById("league").value.trim();
            const date = document.getElementById("date").value.trim();
            const rawData = document.getElementById("raw-data").value.trim();
            const token = document.getElementById("github-token").value.trim();

            if (!league || !date || !rawData || !token) {
                throw new Error("One or more required fields are empty");
            }

            // Preserve pasted rows exactly as-is (Sheets/Excel style)
            const rows = rawData
                .split("\n")
                .map(r => r.replace(/\r/g, "").trim())
                .filter(r => r.length > 0)
                .map(r => r.split("\t"));

            if (rows.length === 0) {
                throw new Error("No tabular rows detected in pasted data");
            }

            // Build XLSX
            const wb = XLSX.utils.book_new();
            const ws = XLSX.utils.aoa_to_sheet(rows);
            XLSX.utils.book_append_sheet(wb, ws, "data");

            const xlsxArrayBuffer = XLSX.write(wb, {
                bookType: "xlsx",
                type: "array"
            });

            const filename = `win_prob_${league}_${date}.xlsx`;

            await commitToGitHub({
                token,
                filename,
                arrayBuffer: xlsxArrayBuffer
            });

            alert(
                "SUCCESS\n\n" +
                "File saved.\n\n" +
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
   GitHub Commit (binary-safe)
   ========================= */

async function commitToGitHub({ token, filename, arrayBuffer }) {
    const owner = "Clownworldenjoyer76";
    const repo = "bet_tracker";
    const path = `docs/win/${filename}`;

    // ArrayBuffer → Base64 (safe for binary XLSX)
    const bytes = new Uint8Array(arrayBuffer);
    let binary = "";
    for (let i = 0; i < bytes.length; i++) {
        binary += String.fromCharCode(bytes[i]);
    }
    const encodedContent = btoa(binary);

    const apiUrl = `https://api.github.com/repos/${owner}/${repo}/contents/${path}`;

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
