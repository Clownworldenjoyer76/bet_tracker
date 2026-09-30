    function wrapPickCards() {
      document.querySelectorAll('.league-column').forEach(col => {
        const allCards = [...col.querySelectorAll('.pick-card')];
        const directCards = [...col.querySelectorAll(':scope > .pick-card')];

        if (allCards.length === 0 && directCards.length === 0) {
          col.style.display = 'none';
          return;
        }

        col.style.display = '';

        if (directCards.length === 0) return;

        let grid = col.querySelector(':scope > .league-cards');

        if (!grid) {
          grid = document.createElement('div');
          grid.className = 'league-cards';
          directCards[0].before(grid);
        }

        directCards.forEach(card => grid.appendChild(card));
      });
    }

    const observer = new MutationObserver(() => wrapPickCards());
    const games = document.getElementById('games');

    if (games) {
      observer.observe(games, { childList: true, subtree: true });
      wrapPickCards();
    }
  
