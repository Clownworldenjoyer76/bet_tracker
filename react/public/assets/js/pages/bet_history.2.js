var activeLeagueSub = 'all';

document.getElementById('league-controls').addEventListener('click', function(event) {
  var pill = event.target.closest('.league-pill[data-league]');
  if (!pill || pill.disabled) return;
  activeLeagueSub = pill.dataset.leagueSub || 'all';
}, true);
