// TOOLS: Read
// WHY: Claude reads test reports and PDFs, sees mostly-green results, and commits
// without enumerating every FAIL/WARN/timeout.

const REPORT_FILE_PATTERNS = [
  /\.report/i, /report\./i, /results?\./i, /test[-_]?results?/i,
  /coverage/i, /\.pdf$/i, /summary/i, /health[-_]?check/i,
];

module.exports = function(input) {
  if (input.tool_name !== "Read") return null;
  const params = input.tool_input || {};

  const filePath = String(params.file_path || "");
  if (!filePath) return null;

  const base = filePath.replace(/\\/g, "/").split("/").pop() || "";
  let isReport = REPORT_FILE_PATTERNS.some((p) => p.test(base));

  if (!isReport) {
    const dirPart = filePath.replace(/\\/g, "/");
    if (/\/reports?\//i.test(dirPart) || /\/results?\//i.test(dirPart)) {
      isReport = true;
    }
  }

  if (!isReport) return null;

  return {
    message:
      "REPORT FILE READ — Review checklist before acting on results.\n\n" +
      `File: ${base}\n\n` +
      "Before committing or declaring results:\n" +
      "  1. List EVERY FAIL, WARN, timeout, error, and empty section in this report\n" +
      "  2. For each: is it a real bug, expected behavior, or needs investigation?\n" +
      "  3. File a TODO for each unresolved issue\n" +
      "  4. Check what's MISSING from the report that should be there\n" +
      "  5. Only then commit or declare results\n\n" +
      "Do NOT skim and assume green. Enumerate every issue explicitly.",
  };
};
