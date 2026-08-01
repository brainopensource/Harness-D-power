import type React from "react";
import { statusGlyph } from "./tokens.js";

export type StatusType =
  | "idle"
  | "running"
  | "frozen"
  | "tainted"
  | "success"
  | "failure"
  | "warning"
  | "pending";

export interface StatusBadgeProps {
  status: StatusType;
  label?: string;
  className?: string;
}

const statusColors: Record<StatusType, { bg: string; text: string; border: string }> = {
  idle: { bg: "bg-gray-800", text: "text-gray-300", border: "border-gray-700" },
  running: { bg: "bg-blue-950", text: "text-blue-400", border: "border-blue-800" },
  frozen: { bg: "bg-sky-950", text: "text-sky-300", border: "border-sky-700" },
  tainted: { bg: "bg-emerald-950", text: "text-emerald-400", border: "border-emerald-700" },
  success: { bg: "bg-green-950", text: "text-green-400", border: "border-green-800" },
  failure: { bg: "bg-red-950", text: "text-red-400", border: "border-red-800" },
  warning: { bg: "bg-amber-950", text: "text-amber-400", border: "border-amber-700" },
  pending: { bg: "bg-purple-950", text: "text-purple-400", border: "border-purple-800" },
};

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, label, className = "" }) => {
  const glyph =
    statusGlyph[status === "failure" ? "failure" : status === "warning" ? "warning" : status] ||
    "•";
  const colors = statusColors[status] || statusColors.idle;
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-mono font-medium border ${colors.bg} ${colors.text} ${colors.border} ${className}`}
      data-testid="status-badge"
      data-status={status}
    >
      <span className="text-xs">{glyph}</span>
      <span>{label || status.toUpperCase()}</span>
    </span>
  );
};

export interface TokenGaugeProps {
  usedTokens: number;
  maxTokens: number;
  costUsd?: number;
  className?: string;
}

export const TokenGauge: React.FC<TokenGaugeProps> = ({
  usedTokens,
  maxTokens,
  costUsd,
  className = "",
}) => {
  const percentage = Math.min(100, Math.max(0, Math.round((usedTokens / maxTokens) * 100)));
  const isHigh = percentage > 85;
  return (
    <div
      className={`p-3 bg-gray-900 border border-gray-800 rounded-lg ${className}`}
      data-testid="token-gauge"
    >
      <div className="flex justify-between items-center text-xs font-mono mb-1.5 text-gray-400">
        <span>TOKEN SPEND</span>
        <span>
          {usedTokens.toLocaleString()} / {maxTokens.toLocaleString()} ({percentage}%)
        </span>
      </div>
      <div className="w-full bg-gray-800 h-2 rounded-full overflow-hidden">
        <div
          className={`h-full transition-all duration-300 ${isHigh ? "bg-amber-500" : "bg-purple-500"}`}
          style={{ width: `${percentage}%` }}
        />
      </div>
      {costUsd !== undefined && (
        <div className="mt-1.5 text-right text-xs font-mono text-emerald-400">
          ${costUsd.toFixed(4)} USD
        </div>
      )}
    </div>
  );
};

export interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon?: React.ReactNode;
  className?: string;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  subtitle,
  icon,
  className = "",
}) => {
  return (
    <div
      className={`p-4 bg-gray-900 border border-gray-800 rounded-lg ${className}`}
      data-testid="metric-card"
    >
      <div className="flex justify-between items-start text-xs font-mono text-gray-400 mb-1">
        <span>{title}</span>
        {icon && <span>{icon}</span>}
      </div>
      <div className="text-xl font-bold font-mono text-gray-100">{value}</div>
      {subtitle && <div className="text-xs text-gray-500 mt-1">{subtitle}</div>}
    </div>
  );
};

export interface CodeSnippetProps {
  code: string;
  language?: string;
  className?: string;
}

export const CodeSnippet: React.FC<CodeSnippetProps> = ({
  code,
  language = "text",
  className = "",
}) => {
  return (
    <pre
      className={`p-3 bg-gray-950 text-gray-200 border border-gray-800 rounded-lg text-xs font-mono overflow-x-auto ${className}`}
      data-testid="code-snippet"
      data-language={language}
    >
      <code>{code}</code>
    </pre>
  );
};

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "danger" | "ghost";
  size?: "sm" | "md" | "lg";
}

export const Button: React.FC<ButtonProps> = ({
  children,
  variant = "primary",
  size = "md",
  className = "",
  ...props
}) => {
  const variantStyles = {
    primary: "bg-purple-600 hover:bg-purple-500 text-white border-purple-500",
    secondary: "bg-gray-800 hover:bg-gray-700 text-gray-200 border-gray-700",
    danger: "bg-red-600 hover:bg-red-500 text-white border-red-500",
    ghost: "bg-transparent hover:bg-gray-800 text-gray-300 border-transparent",
  };
  const sizeStyles = {
    sm: "px-2.5 py-1 text-xs",
    md: "px-3.5 py-1.5 text-sm",
    lg: "px-5 py-2.5 text-base",
  };

  return (
    <button
      className={`inline-flex items-center justify-center font-medium font-mono rounded border transition-colors ${variantStyles[variant]} ${sizeStyles[size]} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
};
