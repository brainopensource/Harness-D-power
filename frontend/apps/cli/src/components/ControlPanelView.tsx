import React, { useState } from "react";
import { Box, Text, useInput } from "ink";
import { ControlCard } from "@sagiha/protocol";

export interface ControlPanelViewProps {
  cards: ControlCard[];
  onToggleCard: (id: string) => void;
  isFocused: boolean;
}

export const ControlPanelView: React.FC<ControlPanelViewProps> = ({
  cards,
  onToggleCard,
  isFocused,
}) => {
  const [selectedIndex, setSelectedIndex] = useState(0);

  useInput(
    (input, key) => {
      if (!isFocused) return;
      if (key.downArrow) {
        setSelectedIndex((prev) => (prev + 1) % cards.length);
      }
      if (key.upArrow) {
        setSelectedIndex((prev) => (prev - 1 + cards.length) % cards.length);
      }
      if (key.return || input === " ") {
        const card = cards[selectedIndex];
        if (card) {
          onToggleCard(card.id);
        }
      }
    },
    { isActive: isFocused },
  );

  return (
    <Box flexDirection="column" flexGrow={1} borderStyle="single" borderColor={isFocused ? "cyan" : "gray"} paddingX={1}>
      <Box justifyContent="space-between" marginBottom={1}>
        <Text bold color={isFocused ? "cyan" : "white"}>
          CONTROL PANEL & KERNEL SERVICES ({cards.length} modules)
        </Text>
        <Text color="dim">Navigate with Up/Down arrows | Press Enter to toggle</Text>
      </Box>

      <Box flexDirection="column" gap={1}>
        {cards.map((card, idx) => {
          const isSelected = isFocused && selectedIndex === idx;
          const statusColor = card.status === "active" ? "green" : card.status === "warning" ? "yellow" : "gray";

          return (
            <Box
              key={card.id}
              borderStyle={isSelected ? "bold" : "single"}
              borderColor={isSelected ? "magenta" : "gray"}
              paddingX={1}
              flexDirection="column"
            >
              <Box justifyContent="space-between">
                <Text bold color={isSelected ? "magenta" : "white"}>
                  {isSelected ? "❯ " : "  "}
                  {card.title}
                </Text>
                <Text color={statusColor} bold>
                  [{card.status.toUpperCase()}]
                </Text>
              </Box>
              <Box marginLeft={2}>
                <Text color="dim">{card.description}</Text>
              </Box>
            </Box>
          );
        })}
      </Box>
    </Box>
  );
};
