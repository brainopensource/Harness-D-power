import { Box, Text, useInput } from "ink";
import type React from "react";

export interface SteerInputProps {
  onPause: () => void;
  onResume: () => void;
  onSteer: (instruction: string) => void;
  onApproveTaint: () => void;
  onQuit: () => void;
}

export const SteerInput: React.FC<SteerInputProps> = ({
  onPause,
  onResume,
  onApproveTaint,
  onQuit,
}) => {
  useInput((input, _key) => {
    const key = input.toLowerCase();
    if (key === "p") onPause();
    else if (key === "r") onResume();
    else if (key === "a") onApproveTaint();
    else if (key === "q") onQuit();
  });

  return (
    <Box borderStyle="single" borderColor="cyan" paddingX={1} flexDirection="column">
      <Text bold color="cyan">
        [KEYBOARD STEERING CONTROL]
      </Text>
      <Box gap={2} marginTop={1}>
        <Text>[P] Pause</Text>
        <Text>[R] Resume</Text>
        <Text>[A] Approve Taint</Text>
        <Text>[Q] Quit</Text>
      </Box>
    </Box>
  );
};
