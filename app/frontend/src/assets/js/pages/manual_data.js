    const OWNER = "Clownworldenjoyer76";
    const REPO  = "bet_tracker";

    const WORKFLOW_FILE = "_manual_intake.yml";

    const REF = "main";

    const MARKET_MAP = {
      soccer: ["Bundesliga", "MLS", "EPL", "La Liga", "Ligue 1", "Serie A"],
      mma: ["UFC"]
    };

    function normalizeKey(value) {
      return (value || "")
        .trim()
        .toLowerCase()
        .replace(/\s+/g, "")
        .replace(/_/g, "");
    }

    function updateMarkets() {
      const l = document.getElementById("league").value;
      const mSel = document.getElementById("market");

      mSel.innerHTML = "";

      if (!l || !MARKET_MAP[l]) {
        mSel.innerHTML = "<option value=''>-- placeholder --</option>";
        updateSources();
        return;
      }

      MARKET_MAP[l].forEach(m => {
        const opt = document.createElement("option");
        opt.value = typeof m === "object" ? m.val : m;
        opt.textContent = typeof m === "object" ? m.text : m;
        mSel.appendChild(opt);
      });

      updateSources();
    }

    function updateSources() {
      const l = document.getElementById("league").value;
      const m = document.getElementById("market").value;
      const sSel = document.getElementById("source");

      if (l === "mma" && m === "UFC") {
        sSel.value = "Predictions";
      }
    }

    async function dispatch() {
      const league = document.getElementById("league").value.trim();
      const market = document.getElementById("market").value.trim();
      const source = document.getElementById("source").value.trim();
      const token  = document.getElementById("token").value.trim();
      const raw    = document.getElementById("raw").value;
      const out    = document.getElementById("out");
      const btn    = document.getElementById("btn");
      const status = document.getElementById("status");

      if (!league || !market || !source || !token || !raw.trim()) {
        out.className = "failure";
        out.textContent = "Major Failure Bro";
        status.className = "";
        status.textContent = "Missing Input";
        return;
      }

      const workflowFile = WORKFLOW_FILE;

      btn.classList.add("submitting");
      btn.disabled = true;
      btn.textContent = "Processing...";
      out.className = "";
      out.textContent = `Submitting to ${workflowFile}...`;
      status.className = "loading";
      status.textContent = "Submitting";

      try {
        const url = `https://api.github.com/repos/${OWNER}/${REPO}/actions/workflows/${workflowFile}/dispatches`;

        const res = await fetch(url, {
          method: "POST",
          headers: {
            "Accept": "application/vnd.github+json",
            "Authorization": `Bearer ${token}`,
            "Content-Type": "application/json"
          },
          body: JSON.stringify({
            ref: REF,
            inputs: {
              league,
              market,
              source,
              raw_text: raw
            }
          })
        });

        if (res.status === 204) {
          out.className = "success";
          out.textContent = `Successfully Submitted: ${workflowFile}`;
          status.className = "";
          status.textContent = "Submitted";
        } else {
          throw new Error();
        }
      } catch (e) {
        out.className = "failure";
        out.textContent = `Major Failure Bro: ${workflowFile}`;
        status.className = "";
        status.textContent = "Failed";
      } finally {
        btn.classList.remove("submitting");
        btn.disabled = false;
        btn.textContent = "Create File";
      }
    }
  
