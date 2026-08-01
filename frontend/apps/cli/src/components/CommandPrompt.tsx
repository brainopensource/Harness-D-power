import React, { useState } from "react";
import { Box, Text, useInput } from "ink";

export interface CommandPromptProps {
  onSubmit: (command: string) => void;
  history: string[];
  isFocused: boolean;
}

const COMMAND_SUGGESTIONS = [
  "/status",
  "/logs --tail",
  "/pause",
  "/resume",
  "/restart",
  "/help",
  "/clear",
];

export const CommandPrompt: React.FC<CommandPromptProps> = ({
  onSubmit,
  history,
  isFocused,
}) => {
  const [value, setValue] = useState("");
  const [historyIndex, setHistoryIndex] = useState(-1);

  // Auto-completion match based on input
  const matchingSuggestion = value.startsWith("/")
    ? COMMAND_SUGGESTIONS.find((cmd) => cmd.startsWith(value) && cmd !== value)
    : undefined;

  useInput(
    (input, key) => {
      if (!isFocused) return;

      if (key.return) {
        if (value.trim().length > 0) {
          onSubmit(value.trim());
          setValue("");
          setHistoryIndex(-1);
        }
        return;
      }

      if (key.tab && matchingSuggestion) {
        setValue(matchingSuggestion);
        return;
      }

      if (key.upArrow) {
        if (history.length > 0) {
          const nextIndex = Math.min(historyIndex + 1, history.length - 1);
          setHistoryIndex(nextIndex);
          setValue(history[nextIndex] || "");
        }
        return;
      }

      if (key.downArrow) {
        if (historyIndex > 0) {
          const nextIndex = historyIndex - 1;
          setHistoryIndex(nextIndex);
          setValue(history[nextIndex] || "");
        } else if (historyIndex === 0) {
          setHistoryIndex(-1);
          setValue("");
        }
        return;
      }

      if (key.backspace || key.delete) {
        setValue((prev) => prev.slice(0, -1));
        return;
      }

      // Append normal text characters
      if (input && !key.ctrl && !key.meta) {
        setValue((prev) => prev + input);
      }
    },
    { isActive: isFocused },
  );

  return (
    <Box flexDirection="column" marginTop={1}>
      {/* Auto-suggestion preview line */}
      {matchingSuggestion && isFocused && (
        <Box paddingX={1}>
          <Text color="dim">
            Suggestion: <Text color="yellow">{matchingSuggestion}</Text> (Press <Text color="cyan">Tab</Text> to complete)
          </Text>
        </Box>
      )}

      {/* Input box */}
      <Box
        borderStyle="single"
        borderColor={isFocused ? "cyan" : "gray"}
        paddingX={1}
        justifyContent="space-between"
      >
        <Box flexGrow={1}>
          <Text bold color={isFocused ? "cyan" : "gray"}>
            ❯{" "}
          </Text>
          <Text color="white">{value}</Text>
          {isFocused && <Text color="cyan">█</Text>}
        </Box>

        <Text color="dim">
          {historyIndex >= 0 ? `History [${historyIndex + 1}/${history.length}]` : "Type / for commands"}
        </Text>
      </Box>
    </Box>
  );
};
