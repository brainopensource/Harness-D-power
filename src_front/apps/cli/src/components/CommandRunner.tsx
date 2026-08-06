import React from "react";
import { Box, Text, useInput } from "ink";
import { MockCassettePlayer } from "@aether/mock-server";

interface Props {
  player: MockCassettePlayer;
  onPlay: (speed: number) => void;
  onPause: () => void;
  onStep: () => void;
  onSwitchCassette: () => void;
}

export const CommandRunner: React.FC<Props> = ({
  player,
  onPlay,
  onPause,
  onStep,
  onSwitchCassette,
}) => {
  useInput((input, key) => {
    if (input === "p") {
      if (player.activeIsPlaying) {
        onPause();
      } else {
        onPlay(1.0);
      }
    } else if (input === "1") {
      onPlay(1.0);
    } else if (input === "2") {
      onPlay(2.0);
    } else if (input === "5") {
      onPlay(5.0);
    } else if (input === "s") {
      onStep();
    } else if (input === "c") {
      onSwitchCassette();
    }
  });

  return (
    <Box flexDirection="column" borderStyle="single" borderColor="green" paddingX={1}>
      <Text bold color="green">
        ⌨️ Controls & Keybindings
      </Text>
      <Box gap={2}>
        <Text color="white">[P] Play/Pause</Text>
        <Text color="white">[1] 1x Speed</Text>
        <Text color="white">[2] 2x Speed</Text>
        <Text color="white">[5] 5x Speed</Text>
        <Text color="white">[S] Step Forward</Text>
        <Text color="white">[C] Switch Cassette</Text>
      </Box>
      <Box marginTop={0}>
        <Text color="gray">
          Status: <Text color="yellow">{player.activeIsPlaying ? "PLAYING" : "PAUSED"}</Text> | Step: {player.position}/{player.totalSteps}
        </Text>
      </Box>
    </Box>
  );
};
