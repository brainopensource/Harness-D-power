import React, { useState, useEffect } from "react";
import { Box } from "ink";
import { useAetherStream } from "@aether/core";
import {
  MockCassettePlayer,
  sweBenchPassCassette,
  repairLoopAblationCassette,
} from "@aether/mock-server";
import { Header } from "./components/Header";
import { BudgetMeter } from "./components/BudgetMeter";
import { TurnLogStream } from "./components/TurnLogStream";
import { CommandRunner } from "./components/CommandRunner";

export const App: React.FC = () => {
  const [player] = useState(() => new MockCassettePlayer());
  const [cassetteIndex, setCassetteIndex] = useState(0);

  const cassettes = [
    { name: "swe_bench_pass.json", data: sweBenchPassCassette },
    { name: "repair_loop_ablation.json", data: repairLoopAblationCassette },
  ];

  useEffect(() => {
    player.loadCassetteData(cassettes[cassetteIndex].data);
    return () => {
      player.stop();
    };
  }, [cassetteIndex, player]);

  const { events } = useAetherStream(player);

  const handlePlay = (speed: number) => {
    player.play(speed);
  };

  const handlePause = () => {
    player.pause();
  };

  const handleStep = () => {
    player.stepForward();
  };

  const handleSwitchCassette = () => {
    const nextIdx = (cassetteIndex + 1) % cassettes.length;
    setCassetteIndex(nextIdx);
  };

  return (
    <Box flexDirection="column" padding={1}>
      <Header />
      <BudgetMeter />
      <TurnLogStream events={events} />
      <CommandRunner
        player={player}
        onPlay={handlePlay}
        onPause={handlePause}
        onStep={handleStep}
        onSwitchCassette={handleSwitchCassette}
      />
    </Box>
  );
};
