import type React from "react";

export type NavView = "cockpit" | "dag" | "context" | "code" | "exporter" | "swarm";

export interface MainLayoutProps {
  currentView: NavView;
  onSelectView: (view: NavView) => void;
  children: React.ReactNode;
}

const navItems: { id: NavView; label: string; icon: string }[] = [
  { id: "cockpit", label: "Agent Cockpit", icon: "⚡" },
  { id: "dag", label: "Story DAG Graph", icon: "🕸" },
  { id: "context", label: "Context Inspector", icon: "🧠" },
  { id: "code", label: "Code Intelligence", icon: "🔍" },
  { id: "exporter", label: "Trace Exporter", icon: "📦" },
  { id: "swarm", label: "AETHER Swarm", icon: "🐝" },
];

export const MainLayout: React.FC<MainLayoutProps> = ({ currentView, onSelectView, children }) => {
  return (
    <div className="flex h-screen bg-[#0A0D14] text-gray-100 font-sans overflow-hidden">
      {/* Sidebar */}
      <aside className="w-64 border-r border-gray-800 bg-gray-950 flex flex-col justify-between">
        <div>
          <div className="p-4 border-b border-gray-800 flex items-center gap-2">
            <span className="text-xl">🌌</span>
            <div>
              <div className="font-bold text-sm font-mono tracking-wider text-purple-400">
                SAGIHA :: AETHER
              </div>
              <div className="text-[10px] text-gray-500 font-mono">AUTONOMOUS AGENT HARNESS</div>
            </div>
          </div>

          <nav className="p-3 space-y-1">
            {navItems.map((item) => {
              const active = currentView === item.id;
              return (
                <button
                  type="button"
                  key={item.id}
                  onClick={() => onSelectView(item.id)}
                  className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-mono transition-colors ${
                    active
                      ? "bg-purple-950/60 text-purple-300 border border-purple-800/60 font-semibold"
                      : "text-gray-400 hover:bg-gray-900 hover:text-gray-200 border border-transparent"
                  }`}
                >
                  <span className="text-base">{item.icon}</span>
                  <span>{item.label}</span>
                </button>
              );
            })}
          </nav>
        </div>

        <div className="p-4 border-t border-gray-800 text-[11px] font-mono text-gray-500">
          <div>TAURI V2 DESKTOP SHELL</div>
          <div className="text-emerald-500 font-medium mt-0.5">● MICROKERNEL DISPATCH OK</div>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col overflow-auto bg-[#0A0D14]">{children}</main>
    </div>
  );
};
