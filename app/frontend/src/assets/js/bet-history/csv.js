function parseCSV(text) {
  var rows = [];
  var current = [];
  var field = '';
  var inQuotes = false;

  for (var i = 0; i < text.length; i++) {
    var char = text[i];
    var next = text[i + 1];

    if (char === '"' && inQuotes && next === '"') {
      field += '"';
      i++;
    } else if (char === '"') {
      inQuotes = !inQuotes;
    } else if (char === ',' && !inQuotes) {
      current.push(field);
      field = '';
    } else if ((char === '\n' || char === '\r') && !inQuotes) {
      if (char === '\r' && next === '\n') i++;
      current.push(field);
      field = '';

      if (current.some(function(v) {
        return v.trim() !== '';
      })) {
        rows.push(current);
      }

      current = [];
    } else {
      field += char;
    }
  }

  if (field || current.length) {
    current.push(field);

    if (current.some(function(v) {
      return v.trim() !== '';
    })) {
      rows.push(current);
    }
  }

  if (rows.length < 2) return [];

  var headers = rows[0].map(function(h) {
    return h.trim().toLowerCase().replace(/"/g, '');
  });

  return rows.slice(1).map(function(row) {
    var obj = {};

    headers.forEach(function(h, i) {
      obj[h] = (row[i] || '').trim().replace(/^"|"$/g, '');
    });

    return obj;
  });
}
