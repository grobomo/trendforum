import { definePluginEntry } from "openclaw/plugin-sdk/plugin-entry";

export default definePluginEntry({
  id: "cron-enforce",
  name: "Cron Polling Enforcer",
  description:
    "Enforces that cron-triggered poll messages actually run the polling script",

  register(api) {
    // Pattern that matches cron poll system events
    const POLL_PATTERN =
      /run python3.*poll_all\.py|Unified poll.*poll_all\.py/i;

    // Use before_prompt_build to inject mandatory execution instructions
    // when a cron poll trigger is detected in the conversation
    api.on("before_prompt_build", (event: any) => {
      const messages = event?.messages;
      if (!messages || !Array.isArray(messages)) return;

      // Check the last user/system message for cron poll trigger
      const lastMsg = messages
        .slice()
        .reverse()
        .find(
          (m: any) =>
            m.role === "user" ||
            m.role === "system"
        );

      if (!lastMsg) return;

      const content =
        typeof lastMsg.content === "string"
          ? lastMsg.content
          : Array.isArray(lastMsg.content)
            ? lastMsg.content
                .filter((b: any) => b.type === "text")
                .map((b: any) => b.text)
                .join(" ")
            : "";

      if (!POLL_PATTERN.test(content)) return;

      // Inject enforcement context that the agent cannot ignore
      // prependContext is prepended before the user message
      api.logger.info(
        "[cron-enforce] Detected poll cron trigger — injecting enforcement instructions"
      );

      return {
        prependContext: [
          "⚠️ CRON POLL ENFORCEMENT (plugin-injected, non-negotiable):",
          "You MUST execute: python3 /home/ubu/.openclaw/workspace/scripts/poll_all.py",
          "You MUST NOT reply HEARTBEAT_OK without first running the script.",
          "You MUST NOT skip, summarize, or defer the polling script execution.",
          "If the script produces output, handle each section per the cron instructions.",
          "If the script produces no output, only then may you reply NO_REPLY or take no action.",
          "Also read and follow HEARTBEAT.md tasks after running the poll.",
          "FAILURE TO EXECUTE THE SCRIPT IS A POLICY VIOLATION.",
        ].join("\n"),
      };
    });

    api.logger.info("[cron-enforce] Plugin registered successfully");
  },
});
