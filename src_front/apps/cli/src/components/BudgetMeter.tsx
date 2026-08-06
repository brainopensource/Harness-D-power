import React from "react";
import { Box, Text } from "ink";
import { useBudget } from "@aether/core";

export const BudgetMeter: React.FC = () => {
  const { reserved, committed, remaining } = useBudget();

  const formatUsd = (micros: number) => `$${(micros / 1000000).toFixed(4)}`;

  return (
    <Box flexDirection="column" borderStyle="single" borderColor="blue" paddingX={1} marginY={1}>
      <Text bold color="blue">
        💰 Budget Ledger (Integer Dims)
      </Text>
      <Box justifyContent="space-between" marginY={0}>
        <Box gap={1}>
          <Text color="gray">Reserved:</Text>
          <Text color="yellow">{formatUsd(reserved.usdMicros)}</Text>
          <Text color="gray">({reserved.promptTokens + reserved.completionTokens} tok)</Text>
        </Box>
        <Box gap={1}>
          <Text color="gray">Committed:</Text>
          <Text color="green">{formatUsd(committed.usdMicros)}</Text>
          <Text color="gray">({committed.promptTokens + committed.completionTokens} tok)</Text>
        </Box>
        <Box gap={1}>
          <Text color="gray">Remaining:</Text>
          <Text color="cyan">{formatUsd(remaining.usdMicros)}</Text>
        </Box>
      </Box>
    </Box>
  );
};
