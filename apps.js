// apps.js
// GUARANTEED EXECUTION DIAGNOSTIC VERSION

// 1) Prove the file is loaded at all
alert("apps.js LOADED");

// 2) Prove DOMContentLoaded fires
document.addEventListener("DOMContentLoaded", () => {
    alert("DOM CONTENT LOADED");

    const form = document.getElementById("win-prob-form");

    if (!form) {
        alert("FORM NOT FOUND");
        return;
    }

    // 3) Prove submit handler fires
    form.addEventListener("submit", async (e) => {
        e.preventDefault();

        alert("SUBMIT HANDLER FIRED");

        try {
            const league = document.getElementById("league").value.trim();
            const date = document.getElementById("date").value.trim();
            const rawData = document.getElementById("raw-data").value.trim();
            const token = document.getElementById("github-token").value.trim();

            if (!league || !date || !rawData || !token) {
                throw new Error("One or more required fields are empty");
            }

            alert("INPUTS READ SUCCESSFULLY");

            // STOP HERE — do not attempt GitHub yet
            alert(
                "SUCCESS (DIAGNOSTIC)\n\n" +
                "JavaScript is executing correctly.\n" +
                "Form submission works.\n\n" +
                "Next step is GitHub commit logic."
            );

        } catch (err) {
            alert(
                "FAILED (DIAGNOSTIC)\n\n" +
                err.message
            );
        }
    });
});
