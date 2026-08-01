import React from "react";
import { Box, Text } from "ink";
import { LogEntry, LogLevel, TrajectoryStep } from "@sagiha/protocol";

export interface LogStreamViewProps {
  logs: LogEntry[];
  steps: TrajectoryStep[];
  filter: "all" | LogLevel;
  onFilterChange: (filter: "all" | LogLevel) => void;
  isFocused: boolean;
}

export const LogStreamView: React.FC<LogStreamViewProps> = ({
  logs,
  steps,
  filter,
  onFilterChange,
  isFocused,
}) => {
  const filteredLogs = logs.filter((log) => filter === "all" || log.level === filter);

  return (
    <Box flexDirection="column" flexGrow={1} borderStyle="single" borderColor={isFocused ? "cyan" : "gray"} paddingX={1}>
      {/* Filter Toolbar */}
      <Box justifyContent="space-between" marginBottom={1}>
        <Text bold color={isFocused ? "cyan" : "white"}>
          LIVE EXECUTION STREAM ({filteredLogs.length} events)
        </Text>
        <Box gap={1}>
          <Text color="dim">Filter:</Text>
          {(["all", "error", "warn", "info", "tool"] as const).map((f) => (
            <Text
              key={f}
              color={filter === f ? "magenta" : "gray"}
              underline={filter === f}
              bold={filter === f}
            >
              [{f.toUpperCase()}]
            </Text>
          ))}
        </Box>
      </Box>

      {/* Log Feed */}
      <Box flexDirection="column" flexGrow={1}>
        {filteredLogs.length === 0 ? (
          <Box paddingY={2} justifyContent="center">
            <Text color="dim">No log entries matching filter [{filter.toUpperCase()}]</Text>
          </Box>
        ) : (
          filteredLogs.slice(0, 10).map((log) => {
            const levelColor =
              log.level === "error"
                ? "red"
                : log.level === "warn"
                ? "yellow"
                : log.level === "tool"
                ? "cyan"
                : "gray";

            return (
              <Box key={log.id} justifyContent="space-between" marginY={0}>
                <Box gap={1}>
                  <Text color="dim">[{log.timestamp.slice(11, 19)}]</Text>
                  <Text color={levelColor} bold>
                    [{log.level.toUpperCase()}]
                  </Text>
                  <Text color="white">{log.message}</Text>
                </Box>
                <Text color="dim">{log.source}</Text>
              </Box>
            );
          })
        )}
      </Box>
    </Box>
  );
};
