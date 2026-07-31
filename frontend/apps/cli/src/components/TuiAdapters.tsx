import { statusGlyph, statusGlyphAscii } from "@sagiha/ui";
import { Box, Text } from "ink";
import type React from "react";

export interface StatusBadgeTuiProps {
  status: "idle" | "running" | "frozen" | "tainted" | "success" | "failure" | "warning" | "pending";
  label?: string;
  useAscii?: boolean;
}

const colorMap = {
  idle: "gray",
  running: "cyan",
  frozen: "blue",
  tainted: "green",
  success: "green",
  failure: "red",
  warning: "yellow",
  pending: "magenta",
} as const;

export const StatusBadgeTui: React.FC<StatusBadgeTuiProps> = ({
  status,
  label,
  useAscii = false,
}) => {
  const glyphs = useAscii ? statusGlyphAscii : statusGlyph;
  const glyph =
    glyphs[status === "failure" ? "failure" : status === "warning" ? "warning" : status] || "•";
  const color = colorMap[status] || "gray";

  return (
    <Box borderStyle="round" borderColor={color} paddingX={1}>
      <Text color={color} bold>
        {glyph} {label || status.toUpperCase()}
      </Text>
    </Box>
  );
};

export interface TokenGaugeTuiProps {
  usedTokens: number;
  maxTokens: number;
  costUsd?: number;
}

export const TokenGaugeTui: React.FC<TokenGaugeTuiProps> = ({ usedTokens, maxTokens, costUsd }) => {
  const percentage = Math.min(100, Math.max(0, Math.round((usedTokens / maxTokens) * 100)));
  const totalBars = 20;
  const filledBars = Math.round((percentage / 100) * totalBars);
  const barStr = "█".repeat(filledBars) + "░".repeat(totalBars - filledBars);
  const color = percentage > 85 ? "yellow" : "magenta";

  return (
    <Box flexDirection="column" borderStyle="single" borderColor="gray" paddingX={1}>
      <Box justifyContent="space-between">
        <Text color="dim">TOKEN SPEND</Text>
        <Text color={color}>
          {usedTokens} / {maxTokens} ({percentage}%)
        </Text>
      </Box>
      <Box marginY={0}>
        <Text color={color}>{barStr}</Text>
      </Box>
      {costUsd !== undefined && (
        <Box justifyContent="flex-end">
          <Text color="green">${costUsd.toFixed(4)} USD</Text>
        </Box>
      )}
    </Box>
  );
};
