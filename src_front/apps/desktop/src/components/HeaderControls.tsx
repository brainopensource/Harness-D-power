import React from "react";
import { Button, Badge } from "@aether/ui-components";
import { Play, Pause, SkipForward, Cpu } from "lucide-react";
import { useEngineStore } from "@aether/core";
import { MockCassettePlayer } from "@aether/mock-server";

interface Props {
  player: MockCassettePlayer;
  activeMode: "mock" | "live";
  cassetteName: string;
  onPlay: (speed: number) => void;
  onPause: () => void;
  onStep: () => void;
  onSwitchCassette: () => void;
  onToggleMode: () => void;
}

export const HeaderControls: React.FC<Props> = ({
  player,
  activeMode,
  cassetteName,
  onPlay,
  onPause,
  onStep,
  onSwitchCassette,
  onToggleMode,
}) => {
  const status = useEngineStore((state) => state.status);
  const activeRunId = useEngineStore((state) => state.activeRunId);

  return (
    <header
      style={{
        height: "56px",
        background: "rgba(15, 23, 42, 0.9)",
        backdropFilter: "blur(16px)",
        borderBottom: "1px solid rgba(255, 255, 255, 0.1)",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "0 20px",
        color: "#f8fafc",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
        <Cpu size={22} color="#38bdf8" />
        <span style={{ fontSize: "16px", fontWeight: 700, letterSpacing: "-0.02em" }}>
          AETHER AGI Orchestrator
        </span>
        <Badge variant={activeMode === "mock" ? "warning" : "success"}>
          {activeMode === "mock" ? "MOCK CASSETTE MODE" : "LIVE ENGINE WS"}
        </Badge>
        <span style={{ fontSize: "12px", color: "#94a3b8" }}>
          Run: <strong style={{ color: "#f8fafc" }}>{activeRunId ?? "swe_bench_001"}</strong>
        </span>
      </div>

      {activeMode === "mock" && (
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <span style={{ fontSize: "12px", color: "#cbd5e1", marginRight: "4px" }}>
            {cassetteName} ({player.position}/{player.totalSteps})
          </span>
          {player.activeIsPlaying ? (
            <Button variant="secondary" size="sm" onClick={onPause}>
              <Pause size={14} /> Pause
            </Button>
          ) : (
            <Button variant="primary" size="sm" onClick={() => onPlay(1.0)}>
              <Play size={14} /> Play
            </Button>
          )}
          <Button variant="secondary" size="sm" onClick={() => onPlay(2.0)}>
            2x
          </Button>
          <Button variant="secondary" size="sm" onClick={() => onPlay(5.0)}>
            5x
          </Button>
          <Button variant="secondary" size="sm" onClick={onStep}>
            <SkipForward size={14} /> Step
          </Button>
          <Button variant="ghost" size="sm" onClick={onSwitchCassette}>
            Switch Cassette
          </Button>
        </div>
      )}

      <div>
        <Button variant="ghost" size="sm" onClick={onToggleMode}>
          Toggle {activeMode === "mock" ? "Live WS" : "Mock"} Mode
        </Button>
      </div>
    </header>
  );
};
