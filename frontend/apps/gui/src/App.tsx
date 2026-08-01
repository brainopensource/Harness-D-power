import React, { useState } from "react";
import { MainLayout, type NavView } from "./layouts/MainLayout.js";
import { AetherSwarmView } from "./views/AetherSwarmView.js";
import { CockpitDashboard } from "./views/CockpitDashboard.js";
import { CodeIntelView } from "./views/CodeIntelView.js";
import { ContextInspector } from "./views/ContextInspector.js";
import { DagVisualizer } from "./views/DagVisualizer.js";
import { ExporterView } from "./views/ExporterView.js";

export function App() {
  const [currentView, setCurrentView] = useState<NavView>("cockpit");

  return (
    <MainLayout currentView={currentView} onSelectView={setCurrentView}>
      {currentView === "cockpit" && <CockpitDashboard />}
      {currentView === "dag" && <DagVisualizer />}
      {currentView === "context" && <ContextInspector />}
      {currentView === "code" && <CodeIntelView />}
      {currentView === "exporter" && <ExporterView />}
      {currentView === "swarm" && <AetherSwarmView />}
    </MainLayout>
  );
}

export default App;
