function doGet(event) {
  const callback = event && event.parameter ? event.parameter.callback : "";
  if (callback && callback !== "mistaLeaderboardSnapshotCallback") {
    throw new Error("Unsupported callback.");
  }

  const body = JSON.stringify(buildPublicLeaderboardSnapshot_());
  const output = callback
    ? ContentService.createTextOutput(callback + "(" + body + ");")
        .setMimeType(ContentService.MimeType.JAVASCRIPT)
    : ContentService.createTextOutput(body)
        .setMimeType(ContentService.MimeType.JSON);
  return output;
}

function buildPublicLeaderboardSnapshot_() {
  const sheet = SpreadsheetApp.openById(LEADERBOARD_SHEET_ID).getSheetByName(LEADERBOARD_TAB);
  if (!sheet) throw new Error("Leaderboard worksheet was not found.");

  const values = sheet.getDataRange().getValues();
  if (!values.length) throw new Error("Leaderboard worksheet is empty.");

  const normalizeHeader = value =>
    String(value || "").trim().toLowerCase().replace(/[_-]+/g, " ").replace(/\s+/g, " ");
  const headers = values[0].map(normalizeHeader);
  const findColumn = aliases => {
    const index = headers.findIndex(header => aliases.includes(header));
    if (index < 0) throw new Error("Leaderboard worksheet is missing a required column.");
    return index;
  };
  const columns = {
    round: findColumn(["round"]),
    displayName: findColumn(["display name"]),
    verifiedSkills: findColumn(["verified skills", "skills"]),
    learningAndBadges: findColumn(["learning & badges", "learning and badges", "learning"]),
    appliedAnalytics: findColumn(["applied analytics", "applied"]),
    totalPoints: findColumn(["total points"])
  };
  const parsePoints = (value, rowNumber, field) => {
    const points = typeof value === "number"
      ? value
      : Number(String(value || "").replace(/,/g, "").trim() || 0);
    if (!Number.isSafeInteger(points) || points < 0) {
      throw new Error("Invalid " + field + " value on leaderboard row " + rowNumber + ".");
    }
    return points;
  };
  const roundsByName = new Map();

  for (let rowIndex = 1; rowIndex < values.length; rowIndex++) {
    const row = values[rowIndex];
    if (row.every(value => value === "" || value === null)) continue;

    const rowNumber = rowIndex + 1;
    const name = String(row[columns.round] || "").trim();
    const displayName = String(row[columns.displayName] || "").trim();
    if (!name || !displayName) {
      throw new Error("Missing round or display name on leaderboard row " + rowNumber + ".");
    }

    const verifiedSkills = parsePoints(row[columns.verifiedSkills], rowNumber, "verified skills");
    const learningAndBadges = parsePoints(row[columns.learningAndBadges], rowNumber, "learning and badges");
    const appliedAnalytics = parsePoints(row[columns.appliedAnalytics], rowNumber, "applied analytics");
    const totalPoints = parsePoints(row[columns.totalPoints], rowNumber, "total points");
    if (totalPoints !== verifiedSkills + learningAndBadges + appliedAnalytics) {
      throw new Error("Point total does not match categories on leaderboard row " + rowNumber + ".");
    }

    if (!roundsByName.has(name)) roundsByName.set(name, []);
    roundsByName.get(name).push({
      displayName,
      verifiedSkills,
      learningAndBadges,
      appliedAnalytics,
      totalPoints
    });
  }

  const rounds = Array.from(roundsByName, ([name, standings]) => {
    standings.sort((a, b) =>
      b.totalPoints - a.totalPoints ||
      a.displayName.toLowerCase().localeCompare(b.displayName.toLowerCase())
    );
    return {
      name,
      standings: standings.map((row, index) => ({rank: index + 1, ...row}))
    };
  });
  if (!rounds.length) rounds.push({name: "Fall 2026", standings: []});

  return {
    snapshotDate: Utilities.formatDate(new Date(), Session.getScriptTimeZone(), "yyyy-MM-dd"),
    rounds
  };
}
