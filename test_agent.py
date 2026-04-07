from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from agent import graph


REPORT_PATH = "test_result.md"


@dataclass
class CaseResult:
	name: str
	prompt: str
	passed: bool
	notes: list[str]
	tools_called: list[str]
	chat_log: list[str]
	final_answer: str
	error: str | None = None


def _extract_chat_log(messages: list[Any]) -> list[str]:
	"""Extract conversation log from graph state for reporting, formatted like a real chat."""
	log_lines = []
	for msg in messages:
		msg_type = msg.__class__.__name__
		if msg_type == "HumanMessage":
			log_lines.append(f"**User**: {msg.content}")
		elif msg_type == "AIMessage":
			if getattr(msg, "tool_calls", None):
				for tc in msg.tool_calls:
					name = tc.get("name", "")
					args = tc.get("args", {})
					log_lines.append(f"**AI (Tool Call)**: `{name}` với arguments: `{args}`")
			content = getattr(msg, "content", None)
			if isinstance(content, str) and content.strip():
				log_lines.append(f"**AI**: {content.strip()}")
		elif msg_type == "ToolMessage":
			log_lines.append(f"**System (Tool Result)**:\n{msg.content}")
	return log_lines


def _extract_tools_and_answer(result: dict[str, Any]) -> tuple[list[str], list[dict[str, Any]], str, list[str]]:
	messages = result.get("messages", [])
	tools_called: list[str] = []
	tool_calls: list[dict[str, Any]] = []
	final_answer = ""
	chat_log = _extract_chat_log(messages)

	for msg in messages:
		calls = getattr(msg, "tool_calls", None)
		if calls:
			for call in calls:
				name = call.get("name") if isinstance(call, dict) else getattr(call, "name", "")
				args = call.get("args") if isinstance(call, dict) else getattr(call, "args", {})
				if name:
					tools_called.append(str(name))
					tool_calls.append({"name": str(name), "args": args})
		content = getattr(msg, "content", None)
		if isinstance(content, str) and content.strip():
			final_answer = content

	return tools_called, tool_calls, final_answer, chat_log


def _count_flight_lines(messages: list[Any]) -> int:
	for msg in messages:
		content = getattr(msg, "content", "")
		if isinstance(content, str) and "Chuyến bay giữa" in content:
			return sum(1 for line in content.splitlines() if line.strip().startswith("- "))
	return 0


def run_case(name: str, prompt: str) -> CaseResult:
	try:
		result = graph.invoke({"messages": [("human", prompt)]})
		tools_called, tool_calls, final_answer, chat_log = _extract_tools_and_answer(result)
		messages = result.get("messages", [])

		notes: list[str] = []
		passed = False

		answer_lower = final_answer.lower()

		if name == "Test 1 — Direct Answer":
			no_tool = len(tools_called) == 0
			asks_more = any(k in answer_lower for k in ["ngân sách", "sở thích", "thời gian"])
			passed = no_tool and asks_more
			notes.append(f"No tool call: {no_tool}")
			notes.append(f"Asked clarification (budget/preference/time): {asks_more}")

		elif name == "Test 2 — Single Tool Call":
			only_flight_tool = tools_called.count("search_flights") >= 1 and set(tools_called) <= {"search_flights"}
			flight_lines = _count_flight_lines(messages)
			has_4_flights = flight_lines >= 4
			passed = only_flight_tool and has_4_flights
			notes.append(f"Tools called: {tools_called}")
			notes.append(f"Detected flight rows: {flight_lines}")

		elif name == "Test 3 — Multi-Step Tool Chaining":
			needed = {"search_flights", "search_hotels", "calculate_budget"}
			called_set = set(tools_called)
			called_all = needed.issubset(called_set)

			found_hanoi_phuquoc = False
			found_budget_5m = False
			for call in tool_calls:
				n = call.get("name")
				args = call.get("args", {})
				if n == "search_flights" and isinstance(args, dict):
					o = str(args.get("origin", "")).lower()
					d = str(args.get("destination", "")).lower()
					if "hà nội" in o and "phú quốc" in d:
						found_hanoi_phuquoc = True
				if n == "calculate_budget" and isinstance(args, dict):
					if str(args.get("total_budget", "")) == "5000000":
						found_budget_5m = True

			has_summary = any(k in answer_lower for k in ["tổng", "chi phí", "gợi ý"])
			passed = called_all and found_hanoi_phuquoc and found_budget_5m and has_summary
			notes.append(f"Tools called: {tools_called}")
			notes.append(f"Called all required tools: {called_all}")
			notes.append(f"Flight args Hanoi->Phu Quoc found: {found_hanoi_phuquoc}")
			notes.append(f"Budget 5,000,000 in calculate_budget found: {found_budget_5m}")

		elif name == "Test 4 — Missing Info / Clarification":
			no_tool = len(tools_called) == 0
			asks_city = "thành phố" in answer_lower or "đi đâu" in answer_lower
			asks_nights = "đêm" in answer_lower or "bao lâu" in answer_lower
			asks_budget = "ngân sách" in answer_lower
			passed = no_tool and asks_city and asks_nights and asks_budget
			notes.append(f"No tool call: {no_tool}")
			notes.append(f"Asked city: {asks_city}")
			notes.append(f"Asked nights/duration: {asks_nights}")
			notes.append(f"Asked budget: {asks_budget}")

		elif name == "Test 5 — Guardrail / Refusal":
			no_tool = len(tools_called) == 0
			refused = any(k in answer_lower for k in ["không", "từ chối", "chỉ hỗ trợ", "du lịch"])
			passed = no_tool and refused
			notes.append(f"No tool call: {no_tool}")
			notes.append(f"Refusal detected: {refused}")

		elif name == "Test 6 — No Flight Found":
			passed = "không tìm thấy chuyến bay" in answer_lower or "chưa có thông tin" in answer_lower
			notes.append("Checks if no flight was successfully handled")

		elif name == "Test 7 — Invalid Budget Input":
			passed = "tổng chi:" in answer_lower or "còn lại" in answer_lower or "vượt ngân sách" in answer_lower
			notes.append("Checks that budget function fallback works even with initial invalid format")

		else:
			notes.append("Unknown test case")

		return CaseResult(
			name=name,
			prompt=prompt,
			passed=passed,
			notes=notes,
			tools_called=tools_called,
			chat_log=chat_log,
			final_answer=final_answer,
			error=None,
		)
	except Exception as ex:
		return CaseResult(
			name=name,
			prompt=prompt,
			passed=False,
			notes=[],
			tools_called=[],
			chat_log=[],
			final_answer="",
			error=f"{type(ex).__name__}: {ex}",
		)


def build_report(results: list[CaseResult]) -> str:
	passed_count = sum(1 for r in results if r.passed)
	lines: list[str] = []
	lines.append("# TravelBuddy Agent Test Results")
	lines.append("")
	lines.append(f"- Generated at: {datetime.now().isoformat(timespec='seconds')}")
	lines.append(f"- Total: {len(results)}")
	lines.append(f"- Passed: {passed_count}")
	lines.append(f"- Failed: {len(results) - passed_count}")
	lines.append("")
	lines.append("## Summary")
	lines.append("")
	lines.append("| Test | Status | Tools Called |")
	lines.append("|---|---|---|")
	for r in results:
		status = "PASS" if r.passed else "FAIL"
		tools = ", ".join(r.tools_called) if r.tools_called else "(none)"
		lines.append(f"| {r.name} | {status} | {tools} |")

	lines.append("")
	lines.append("## Details")
	for r in results:
		lines.append("")
		lines.append(f"### {r.name}")
		lines.append(f"- Prompt: {r.prompt}")
		lines.append(f"- Status: {'PASS' if r.passed else 'FAIL'}")
		if r.error:
			lines.append(f"- Error: {r.error}")
		if r.notes:
			lines.append("- Checks:")
			for note in r.notes:
				lines.append(f"  - {note}")
		lines.append("")
		lines.append("#### Conversation Trace:")
		if r.chat_log:
			for chat_line in r.chat_log:
				lines.append(f"> {chat_line}\n>")
		else:
			lines.append("> (No conversation)")
		
		lines.append("")
		lines.append("#### Final answer:")
		if r.final_answer:
			lines.append("```")
			lines.append(r.final_answer)
			lines.append("```")
		else:
			lines.append("(empty)")

	lines.append("")
	return "\n".join(lines)


def main() -> None:
	cases = [
		(
			"Test 1 — Direct Answer",
			"Xin chào! Tôi đang muốn đi du lịch nhưng chưa biết đi đâu.",
		),
		(
			"Test 2 — Single Tool Call",
			"Tìm giúp tôi chuyến bay từ Hà Nội đi Đà Nẵng",
		),
		(
			"Test 3 — Multi-Step Tool Chaining",
			"Tôi ở Hà Nội, muốn đi Phú Quốc 2 đêm, budget 5 triệu. Tư vấn giúp!",
		),
		(
			"Test 4 — Missing Info / Clarification",
			"Tôi muốn đặt khách sạn",
		),
		(
			"Test 5 — Guardrail / Refusal",
			"Giải giúp tôi bài tập lập trình Python về linked list",
		),
		(
			"Test 6 — No Flight Found",
			"Hãy tìm cho tôi vé máy bay từ Hải Phòng vào Cần Thơ.",
		),
		(
			"Test 7 — Invalid Budget Input",
			"Ngân sách 10 triệu, muốn mua vé bay 3 triệu, khách sạn 8 triệu. Tính phí xem nhé.",
		),
	]

	results = [run_case(name, prompt) for name, prompt in cases]
	report = build_report(results)

	with open(REPORT_PATH, "w", encoding="utf-8") as f:
		f.write(report)

	print(f"Saved report to {REPORT_PATH}")
	for r in results:
		print(f"- {r.name}: {'PASS' if r.passed else 'FAIL'}")


if __name__ == "__main__":
	main()
