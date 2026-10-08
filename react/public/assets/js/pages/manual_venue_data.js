    const OWNER = "Clownworldenjoyer76";
    const REPO  = "bet_tracker";
    const REF   = "main";

    const LEAGUE_CONFIG = {
      MLB: {
        label: "MLB",
        workflowFile: "manual_park_factors.yml",
        outputDir: "docs/win/baseball/mlb/data/park_factors",
        filePrefix: "park",
        variable1Options: [
          { label: "BOTH",  code: "B" },
          { label: "LEFT",  code: "L" },
          { label: "RIGHT", code: "R" }
        ],
        variable2Options: [
          { label: "DAY",         code: "day" },
          { label: "NIGHT",       code: "night" },
          { label: "OPEN AIR",    code: "open_air" },
          { label: "ROOF CLOSED", code: "roof_closed" }
        ]
      }

      /*
      Future league example:

      NBA: {
        label: "NBA",
        workflowFile: "manual_venue_data.yml",
        outputDir: "docs/win/basketball/data/venue_factors",
        filePrefix: "venue",
        variable1Options: [
          { label: "HOME", code: "home" },
          { label: "AWAY", code: "away" }
        ],
        variable2Options: [
          { label: "REGULAR SEASON", code: "regular" },
          { label: "PLAYOFFS", code: "playoffs" }
        ]
      }
      */
    };

    function setSelectOptions(selectElement, options, placeholderText) {
      selectElement.innerHTML = "";

      const placeholder = document.createElement("option");
      placeholder.value = "";
      placeholder.textContent = placeholderText;
      selectElement.appendChild(placeholder);

      options.forEach(option => {
        const opt = document.createElement("option");
        opt.value = option.label;
        opt.textContent = option.label;
        selectElement.appendChild(opt);
      });
    }

    function getLeagueConfig() {
      const league = document.getElementById("league").value;
      return LEAGUE_CONFIG[league] || null;
    }

    function getOptionCode(options, selectedLabel) {
      const found = options.find(option => option.label === selectedLabel);
      return found ? found.code : "";
    }

    function populateLeagues() {
      const leagueSelect = document.getElementById("league");

      leagueSelect.innerHTML = "";

      const placeholder = document.createElement("option");
      placeholder.value = "";
      placeholder.textContent = "-- select --";
      leagueSelect.appendChild(placeholder);

      Object.keys(LEAGUE_CONFIG).forEach(leagueKey => {
        const config = LEAGUE_CONFIG[leagueKey];
        const opt = document.createElement("option");
        opt.value = leagueKey;
        opt.textContent = config.label;
        leagueSelect.appendChild(opt);
      });
    }

    function updateVariable1() {
      const config = getLeagueConfig();
      const variable1Select = document.getElementById("variable1");
      const variable2Select = document.getElementById("variable2");

      if (!config) {
        setSelectOptions(variable1Select, [], "-- select league first --");
        setSelectOptions(variable2Select, [], "-- select variable 1 first --");
        updateTargetPathDisplay();
        return;
      }

      setSelectOptions(variable1Select, config.variable1Options, "-- select --");
      setSelectOptions(variable2Select, [], "-- select variable 1 first --");
      updateTargetPathDisplay();
    }

    function updateVariable2() {
      const config = getLeagueConfig();
      const variable1 = document.getElementById("variable1").value;
      const variable2Select = document.getElementById("variable2");

      if (!config || !variable1) {
        setSelectOptions(variable2Select, [], "-- select variable 1 first --");
        updateTargetPathDisplay();
        return;
      }

      setSelectOptions(variable2Select, config.variable2Options, "-- select --");
      updateTargetPathDisplay();
    }

    function getTargetPath() {
      const config = getLeagueConfig();
      const variable1 = document.getElementById("variable1").value;
      const variable2 = document.getElementById("variable2").value;

      if (!config || !variable1 || !variable2) {
        return "";
      }

      const variable1Code = getOptionCode(config.variable1Options, variable1);
      const variable2Code = getOptionCode(config.variable2Options, variable2);

      if (!variable1Code || !variable2Code) {
        return "";
      }

      return `${config.outputDir}/${config.filePrefix}_${variable1Code}_${variable2Code}.csv`;
    }

    function updateTargetPathDisplay() {
      const targetPath = getTargetPath();
      const targetPathDiv = document.getElementById("targetPath");

      if (!targetPath) {
        targetPathDiv.textContent = "";
        return;
      }

      targetPathDiv.textContent = `Target: ${targetPath}`;
    }

    async function dispatch() {
      const league = document.getElementById("league").value.trim();
      const variable1 = document.getElementById("variable1").value.trim();
      const variable2 = document.getElementById("variable2").value.trim();
      const token = document.getElementById("token").value.trim();
      const raw = document.getElementById("raw").value;
      const out = document.getElementById("out");
      const btn = document.getElementById("btn");
      const status = document.getElementById("status");
      const config = getLeagueConfig();
      const targetPath = getTargetPath();

      if (!config || !league || !variable1 || !variable2 || !token || !raw.trim() || !targetPath) {
        out.className = "failure";
        out.textContent = "Major Failure Bro";
        status.className = "";
        status.textContent = "Missing Input";
        return;
      }

      btn.classList.add("submitting");
      btn.disabled = true;
      btn.textContent = "Processing...";
      out.className = "";
      out.textContent = `Submitting to ${config.workflowFile}...`;
      status.className = "loading";
      status.textContent = "Submitting";

      try {
        const url = `https://api.github.com/repos/${OWNER}/${REPO}/actions/workflows/${config.workflowFile}/dispatches`;

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
              league: league,
              variable_1: variable1,
              variable_2: variable2,
              raw_text: raw,
              target_path: targetPath
            }
          })
        });

        if (res.status === 204) {
          out.className = "success";
          out.textContent = `Successfully Submitted: ${targetPath}`;
          status.className = "";
          status.textContent = "Submitted";
        } else {
          throw new Error();
        }
      } catch (e) {
        out.className = "failure";
        out.textContent = `Major Failure Bro: ${config.workflowFile}`;
        status.className = "";
        status.textContent = "Failed";
      } finally {
        btn.classList.remove("submitting");
        btn.disabled = false;
        btn.textContent = "Create File";
      }
    }

    populateLeagues();
    updateVariable1();
  
