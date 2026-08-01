import { Button, CodeSnippet } from "@sagiha/ui";
import type React from "react";

export interface TaintApprovalModalProps {
  envelopeText?: string;
  toolName?: string;
  onApprove: () => void;
  onReject: () => void;
}

export const TaintApprovalModal: React.FC<TaintApprovalModalProps> = ({
  envelopeText = "<untrusted-data>Scraped API payload with candidate code snippet</untrusted-data>",
  toolName = "apply_edit",
  onApprove,
  onReject,
}) => {
  return (
    <div className="p-6 space-y-6 max-w-2xl bg-gray-950 border border-emerald-800 rounded-xl shadow-2xl font-mono">
      <div className="flex justify-between items-center border-b border-gray-800 pb-3">
        <div className="flex items-center gap-2">
          <span className="text-xl">🛡</span>
          <h2 className="text-base font-bold text-emerald-400">
            MONOTONIC TAINT GATE :: APPROVAL REQUIRED
          </h2>
        </div>
        <span className="text-xs px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-700">
          requires_human=True
        </span>
      </div>

      <p className="text-xs text-gray-300">
        External untrusted data entered context during step execution. Tool call{" "}
        <span className="text-purple-400 font-bold">{toolName}</span> requires explicit human
        authorization.
      </p>

      <div className="space-y-2">
        <div className="text-xs text-gray-400">UNTRUSTED DATA ENVELOPE:</div>
        <CodeSnippet code={envelopeText} language="xml" />
      </div>

      <div className="flex justify-end gap-3 pt-2">
        <Button variant="danger" size="sm" onClick={onReject}>
          ✗ REJECT & REVERT
        </Button>
        <Button variant="primary" size="sm" onClick={onApprove}>
          ✓ APPROVE MUTATION
        </Button>
      </div>
    </div>
  );
};
