import React from "react";
import { Box, Text } from "ink";
import { Provenance } from "@aether/core";

interface Props {
  provenance: Provenance;
  source?: string;
}

export const TaintAuditBadge: React.FC<Props> = ({ provenance, source }) => {
  const getBadgeColor = () => {
    switch (provenance) {
      case Provenance.TRUSTED_SYSTEM:
        return "blue";
      case Provenance.OPERATOR:
        return "cyan";
      case Provenance.AGENT:
        return "magenta";
      case Provenance.UNTRUSTED_EXTERNAL:
        return "red";
      case Provenance.UNTRUSTED_DERIVED:
        return "yellow";
      default:
        return "gray";
    }
  };

  return (
    <Box gap={1}>
      <Text color={getBadgeColor()} bold>
        &lt;{provenance}&gt;
      </Text>
      {source && <Text color="gray">({source})</Text>}
    </Box>
  );
};
