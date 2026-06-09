# Not all agents need LLMs. Rule-based agents are deterministic, free, and instant.

from __future__ import annotations

import asyncio

from agentstatelib import StatePatch


async def priority_classifier(context: dict) -> StatePatch:
    facts = context.get("facts", {})
    customer_message = str(facts.get("customer_message", "")).lower()
    urgency_keywords = [
        "urgent",
        "asap",
        "immediately",
        "critical",
        "broken",
        "down",
        "emergency",
    ]
    matched = [kw for kw in urgency_keywords if kw in customer_message]
    priority = "high" if matched else "normal"
    return StatePatch(
        agent_id="priority_classifier",
        target="tasks.classification",
        value={"priority": priority, "matched_keywords": matched},
        reason="Classified customer message urgency based on keyword matches.",
    )


async def task_router(context: dict) -> StatePatch:
    classification = context.get("tasks", {}).get("classification", {})
    priority = classification.get("priority", "normal")
    team = "support" if priority == "high" else "general"
    return StatePatch(
        agent_id="task_router",
        target="tasks.routing",
        value={"assigned_team": team, "priority": priority},
        reason="Routed task to the appropriate team based on priority.",
    )


async def completion_checker(context: dict) -> StatePatch:
    tasks = context.get("tasks", {})
    if tasks and all(
        getattr(task, "get", lambda k, d=None: None)("status", None) == "done"
        if isinstance(task, dict)
        else False
        for task in tasks.values()
    ):
        return StatePatch(
            agent_id="completion_checker",
            target="status",
            value="complete",
            reason="All tasks are complete.",
        )

    pending_count = sum(
        1
        for task in tasks.values()
        if isinstance(task, dict) and task.get("status") != "done"
    )
    return StatePatch(
        agent_id="completion_checker",
        target="facts.pending_count",
        value=pending_count,
        reason="Counted remaining incomplete tasks.",
    )


async def main():
    context = {
        "facts": {"customer_message": "This is urgent and the system is broken"},
        "tasks": {"t1": {"status": "open"}, "t2": {"status": "done"}},
    }

    p1 = await priority_classifier(context)
    print(p1)

    context["tasks"]["classification"] = p1.value
    p2 = await task_router(context)
    print(p2)

    context["tasks"]["routing"] = p2.value
    p3 = await completion_checker(context)
    print(p3)


if __name__ == "__main__":
    asyncio.run(main())
