import React from "react";
import { Box, Text } from "ink";
import { BridgeEvent } from "@aether/core";
import { GateStatusIndicator } from "./GateStatusIndicator";

interface Props {
  events: BridgeEvent[];
}

export const TurnLogStream: React.FC<Props> = ({ events }) => {
  const recentEvents = events.slice(-8);

  const renderEventItem = (event: BridgeEvent) => {
    const payload = event.payload as any;

    switch (event.eventType) {
      case "RunStarted":
        return (
          <Text color="green" bold>
            🚀 Run [{event.runId}] started with Task [{payload.taskId}]
          </Text>
        );
      case "NodeExecutionStarted":
        return (
          <Text color="cyan">
            ▶ Node [{payload.nodeId}] ({payload.nodeKind}) entered execution...
          </Text>
        );
      case "NodeExecutionFinished":
        return (
          <Box flexDirection="column">
            <Text color="white">
              ✓ Node [{payload.nodeId}] finished
            </Text>
            <GateStatusIndicator gateReport={payload.gateReport} />
          </Box>
        );
      case "ModelStreamDelta":
        return (
          <Text color="yellow" italic>
            💬 Stream Delta [{payload.nodeId}]: {payload.text}
          </Text>
        );
      case "RunCompleted":
        return (
          <Text color="green" bold>
            🎉 Run [{event.runId}] Completed successfully! Score: {payload.finalScore}
          </Text>
        );
      default:
        return (
          <Text color="gray">
            [{event.seq}] {event.eventType}
          </Text>
        );
    }
  };

  return (
    <Box flexDirection="column" borderStyle="single" borderColor="magenta" paddingX={1} minHeight={10}>
      <Text bold color="magenta">
        📜 Real-time Turn Stream & Execution Log
      </Text>
      {recentEvents.length === 0 ? (
        <Text color="gray" italic>
          Waiting for events or cassette playback...
        </Text>
      ) : (
        recentEvents.map((event, idx) => (
          <Box key={`${event.runId}-${event.seq}-${idx}`} marginY={0}>
            {renderEventItem(event)}
          </Box>
        ))
      )}
    </Box>
  );
};
