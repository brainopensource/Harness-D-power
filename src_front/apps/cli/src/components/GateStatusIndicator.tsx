import React from "react";
import { Box, Text } from "ink";
import { GateStatus, GateReport } from "@aether/core";

interface Props {
  gateReport?: GateReport;
}

export const GateStatusIndicator: React.FC<Props> = ({ gateReport }) => {
  if (!gateReport) return null;

  const renderBadge = () => {
    switch (gateReport.status) {
      case GateStatus.PASSED:
        return <Text color="green" bold>[✓ PASSED]</Text>;
      case GateStatus.FAILED:
        return <Text color="red" bold>[✗ FAILED]</Text>;
      case GateStatus.NONE:
        return (
          <Text color="yellow" bold>
            [⚠ INSTRUMENT ERROR - NONE]
          </Text>
        );
      default:
        return <Text color="gray">[UNKNOWN]</Text>;
    }
  };

  return (
    <Box flexDirection="column" marginY={0}>
      <Box gap={1}>
        <Text color="gray">Gate ({gateReport.gate}):</Text>
        {renderBadge()}
        <Text color="white">{gateReport.detail}</Text>
      </Box>
      {gateReport.status === GateStatus.NONE && gateReport.instrumentError && (
        <Box marginLeft={2}>
          <Text color="yellow" italic>
            Detail: {gateReport.instrumentError} (excluded from denominator)
          </Text>
        </Box>
      )}
    </Box>
  );
};
