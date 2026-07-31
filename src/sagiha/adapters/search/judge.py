"""S-2: local LLM judge scorer (`backend="judge"`) — ships **off by default**
(`ScoringConfig.backend = "composite"`).

Judge separation is enforced at config load, not here: `Config.validate_security_invariants`
(`domain/config.py`) already refuses `search.enabled=True` when the `judge` role resolves to the
same `(provider, model)` tuple as `execution` — a judge that is also the generator cannot score
its own candidate honestly. This class trusts that refusal rather than re-checking it.
"""

from __future__ import annotations

import json
import logging

from sagiha.adapters.search.protocols import CandidateOutcome
from sagiha.domain.config import ScoringConfig
from sagiha.domain.content import Message, ModelRequest, TextBlock
from sagiha.domain.work import ReviewFinding, ReviewReport, TaskSpec
from sagiha.ports.model import ModelProvider

logger = logging.getLogger(__name__)

_RUBRIC_VERSION = "s2-judge-v0"

_SYSTEM_PROMPT = (
    "You are a code review judge. You did not write this diff. Score it 0.0-1.0 on whether it "
    "correctly and minimally solves the stated task. Respond with a single JSON object: "
    '{"score": <float 0-1>, "summary": "<one sentence>"}. Nothing else.'
)


class LocalJudgeScorer:
    """Calls the `judge` model role with a fixed rubric and parses a `ReviewReport`.

    Falls back to a score of `0.0` with a `findings` entry on any parse failure — a judge that
    cannot be understood must never silently default to a middling or passing score, since that
    is indistinguishable from "the candidate was mediocre" to anything reading `ReviewReport`
    downstream (the distillation exporter, in particular).
    """

    def __init__(self, config: ScoringConfig, *, model_provider: ModelProvider, model_label: str) -> None:
        self._config = config
        self._model = model_provider
        self._model_label = model_label

    async def score(self, task: TaskSpec, outcome: CandidateOutcome) -> ReviewReport:
        prompt = (
            f"Task: {task.goal}\n\n"
            f"Diff digest: {outcome.diff_digest}\n"
            f"Files changed: {outcome.files_changed}, diff lines: {outcome.diff_lines}\n"
            f"Gate admitted: {outcome.gate_report.admitted if outcome.gate_report else 'unknown'}\n"
        )
        request = ModelRequest(
            messages=[Message(role="user", content=[TextBlock(text=prompt)])],
            system=_SYSTEM_PROMPT,
            role="judge",
        )
        try:
            completion = await self._model.complete(request)
            text = next(
                (b.text for b in completion.message.content if isinstance(b, TextBlock)),
                "",
            )
            parsed = json.loads(text)
            score = max(0.0, min(1.0, float(parsed["score"])))
            summary = str(parsed.get("summary", ""))
        except Exception as exc:  # noqa: BLE001 - any parse/model failure is a scoring failure, not a crash
            logger.warning("LocalJudgeScorer failed to parse judge response: %s", exc)
            score = 0.0
            summary = f"judge scoring failed: {exc}"

        findings = (
            (
                ReviewFinding(
                    path=outcome.worktree_ref,
                    severity="nit",
                    category="correctness",
                    summary=summary,
                ),
            )
            if summary
            else ()
        )
        return ReviewReport(
            score=score,
            findings=findings,
            judge_model=self._model_label,
            rubric_version=_RUBRIC_VERSION,
        )
