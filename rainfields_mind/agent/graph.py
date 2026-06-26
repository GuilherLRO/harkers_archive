"""LangGraph pipeline for synthesizing one weekly Rainfields Mind note."""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph

from index_writer import upsert_week_row
from manifest import Manifest, update_week_record
from paths import MANIFEST_PATH
from prompts import build_user_prompt, load_system_prompt
from state import GraphState, WeeklySynthesis
from tags import append_candidate_tags
from validate import validate_weekly_note
from weeks import dossier_relpaths_for_week, previous_week_id, week_bounds

logger = logging.getLogger(__name__)
MAX_RETRIES = 1


def _build_chat_model(model_name: str) -> ChatOpenAI:
    """Build ChatOpenAI; omit temperature unless explicitly configured.

    Reasoning models (o-series) and some OpenRouter providers reject temperature=0.
    """
    kwargs: dict = {"model": model_name}
    api_base = os.environ.get("OPENAI_API_BASE", "").strip()
    if api_base:
        kwargs["base_url"] = api_base
    raw_temp = os.environ.get("RAINFIELDS_TEMPERATURE", "").strip()
    if raw_temp:
        kwargs["temperature"] = float(raw_temp)
    return ChatOpenAI(**kwargs)


def _load_context(state: GraphState) -> GraphState:
    week_id = state["week_id"]
    rainfields_dir = Path(state["rainfields_dir"])
    dossier_dir = Path(state["dossier_dir"])
    info = week_bounds(week_id)

    dossier_paths = [dossier_dir / Path(relpath).name for relpath in state["dossier_files"]]
    dossier_contents = [
        (f"dossier/{path.name}", path.read_text(encoding="utf-8"))
        for path in dossier_paths
    ]

    previous_week_text: str | None = None
    prev_id = previous_week_id(week_id)
    if prev_id:
        prev_path = rainfields_dir / "weekly" / f"{prev_id}.md"
        if prev_path.exists():
            previous_week_text = prev_path.read_text(encoding="utf-8")

    weekly_path = rainfields_dir / "weekly" / f"{week_id}.md"
    action = "create" if not weekly_path.exists() else "refresh"

    return {
        **state,
        "date_range": info.date_range,
        "action": action,
        "dossier_contents": dossier_contents,
        "previous_week_text": previous_week_text,
        "system_prompt": load_system_prompt(rainfields_dir),
        "retry_count": state.get("retry_count", 0),
    }


def _generate_note(state: GraphState) -> GraphState:
    model_name = state["model"]
    llm = _build_chat_model(model_name)
    structured = llm.with_structured_output(WeeklySynthesis)

    user_prompt = build_user_prompt(
        week_id=state["week_id"],
        date_range=state["date_range"],
        action=state["action"],
        dossier_files=state["dossier_contents"],
        previous_week_text=state.get("previous_week_text"),
    )
    if state.get("validation_errors"):
        user_prompt += (
            "\n\nPrevious output failed validation. Fix these issues:\n"
            + "\n".join(f"- {err}" for err in state["validation_errors"])
        )

    messages = [
        SystemMessage(content=state["system_prompt"]),
        HumanMessage(content=user_prompt),
    ]
    synthesis: WeeklySynthesis = structured.invoke(messages)
    return {
        **state,
        "synthesis": synthesis,
        "reasoning": synthesis.reasoning,
        "weekly_markdown": synthesis.weekly_markdown,
        "index_summary": synthesis.index_summary,
        "proposed_tags": synthesis.proposed_tags,
        "validation_errors": [],
    }


def _validate_output(state: GraphState) -> GraphState:
    expected = set(state["dossier_files"])
    result = validate_weekly_note(
        state["weekly_markdown"],
        week_id=state["week_id"],
        expected_source_files=expected,
    )
    return {
        **state,
        "validation_errors": result.errors,
    }


def _route_after_validate(state: GraphState) -> str:
    if state.get("validation_errors"):
        if state.get("retry_count", 0) < MAX_RETRIES:
            return "retry"
        return "fail"
    return "persist"


def _increment_retry(state: GraphState) -> GraphState:
    return {**state, "retry_count": state.get("retry_count", 0) + 1}


def _persist_outputs(state: GraphState) -> GraphState:
    rainfields_dir = Path(state["rainfields_dir"])
    weekly_dir = rainfields_dir / "weekly"
    weekly_dir.mkdir(parents=True, exist_ok=True)
    weekly_path = weekly_dir / f"{state['week_id']}.md"
    weekly_path.write_text(state["weekly_markdown"].strip() + "\n", encoding="utf-8")

    index_path = rainfields_dir / "index.md"
    index_text = index_path.read_text(encoding="utf-8")
    index_path.write_text(
        upsert_week_row(index_text, state["week_id"], state["index_summary"]),
        encoding="utf-8",
    )

    tags_appended: list[str] = []
    tagging_path = rainfields_dir / "TAGGING_SYSTEM.md"
    tagging_text = tagging_path.read_text(encoding="utf-8")
    updated_tagging, added = append_candidate_tags(tagging_text, state.get("proposed_tags", []))
    if added:
        tagging_path.write_text(updated_tagging, encoding="utf-8")
        tags_appended = [item.tag for item in added]

    dossier_paths = [Path(state["dossier_dir"]) / Path(relpath).name for relpath in state["dossier_files"]]
    manifest = Manifest.load(MANIFEST_PATH)
    update_week_record(
        manifest,
        state["week_id"],
        dossier_paths,
        weekly_path,
        compiled_at=datetime.now(UTC).isoformat(),
    )
    manifest.save(MANIFEST_PATH)

    return {
        **state,
        "weekly_path": str(weekly_path),
        "index_updated": True,
        "tags_appended": tags_appended,
    }


def _fail_validation(state: GraphState) -> GraphState:
    errors = "; ".join(state.get("validation_errors", []))
    return {**state, "error": f"validation failed after retry: {errors}"}


def build_week_graph():
    graph = StateGraph(GraphState)
    graph.add_node("load_context", _load_context)
    graph.add_node("generate_note", _generate_note)
    graph.add_node("validate_output", _validate_output)
    graph.add_node("increment_retry", _increment_retry)
    graph.add_node("persist_outputs", _persist_outputs)
    graph.add_node("fail_validation", _fail_validation)

    graph.add_edge(START, "load_context")
    graph.add_edge("load_context", "generate_note")
    graph.add_edge("generate_note", "validate_output")
    graph.add_conditional_edges(
        "validate_output",
        _route_after_validate,
        {
            "retry": "increment_retry",
            "persist": "persist_outputs",
            "fail": "fail_validation",
        },
    )
    graph.add_edge("increment_retry", "generate_note")
    graph.add_edge("persist_outputs", END)
    graph.add_edge("fail_validation", END)
    return graph.compile()


def run_week_pipeline(
    *,
    week_id: str,
    dossier_files: list[Path],
    rainfields_dir: Path,
    dossier_dir: Path,
    model: str,
) -> GraphState:
    relpaths = dossier_relpaths_for_week(week_id, dossier_files)
    initial: GraphState = {
        "week_id": week_id,
        "dossier_files": relpaths,
        "rainfields_dir": str(rainfields_dir),
        "dossier_dir": str(dossier_dir),
        "model": model,
        "retry_count": 0,
    }
    graph = build_week_graph()
    return graph.invoke(initial)
