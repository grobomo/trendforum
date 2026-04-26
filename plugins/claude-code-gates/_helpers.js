// Shared helpers used across multiple gate modules.

function extractCommitMsg(cmd) {
  const heredocMatch = cmd.match(/-m\s+"\$\(cat\s+<<'?EOF'?\s*\n([\s\S]*?)\nEOF/);
  if (heredocMatch) return heredocMatch[1].trim();
  const mMatch = cmd.match(/-m\s+["']([^"']+)["']/);
  if (mMatch) return mMatch[1].trim();
  return "";
}

function stripQuotedContent(cmd) {
  return cmd
    .replace(/<<\s*['"]?(\w+)['"]?[\s\S]*?\n\1(\s|$)/g, " ")
    .replace(/"[^"]*"/g, '""')
    .replace(/'[^']*'/g, "''");
}

const SECRET_PATTERNS = [
  { name: "AWS Access Key", re: /AKIA[0-9A-Z]{16}/ },
  { name: "AWS Secret Key", re: /[0-9a-zA-Z/+=]{40}(?=\s|"|'|$)/, context: /aws_secret|secret_access|SECRET_KEY/i },
  { name: "Azure Storage Key", re: /[A-Za-z0-9+/]{86}==/ },
  { name: "Azure SAS Token", re: /sig=[A-Za-z0-9%+/=]{20,}/ },
  { name: "GitHub Token", re: /gh[ps]_[A-Za-z0-9_]{36,}/ },
  { name: "Generic API Key", re: /(?:api[_-]?key|apikey|api[_-]?secret)\s*[:=]\s*["']?[A-Za-z0-9_\-]{20,}/i },
  { name: "Generic Password", re: /(?:password|passwd|pwd)\s*[:=]\s*\\?["']?[^\s"']{8,}/i },
  { name: "Generic Token", re: /(?:token|secret|bearer)\s*[:=]\s*\\?["']?[A-Za-z0-9_\-.]{20,}/i },
  { name: "Private Key", re: /-----BEGIN (?:RSA |EC |DSA )?PRIVATE KEY-----/ },
  { name: "Connection String", re: /(?:mongodb|postgres|mysql|redis|amqp):\/\/[^\s]{20,}/ },
];

module.exports = { extractCommitMsg, stripQuotedContent, SECRET_PATTERNS };
