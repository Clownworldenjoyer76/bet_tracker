var baseFilteredRows = filteredRows;

filteredRows = function() {
  return baseFilteredRows().filter(function(r) {
    if (
      activeLeague === 'SOCCER' &&
      activeLeagueSub !== 'all' &&
      r.league_sub !== activeLeagueSub
    ) {
      return false;
    }

    return true;
  });
};
