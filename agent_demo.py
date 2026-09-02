"""
Agent Mini-Demo — SME Compliance Assistant (Milestone 3)
Pipeline: Question -> LLM decides tool -> Tool executes -> LLM uses result -> final answer

Milestone 3 change: query_business_data() and check_requirement() are now
backed by the real business_profile.py and rules_engine.py modules instead
of a hardcoded dict and inline if/else (as they were in Milestone 1/2).

Setup:
    pip install google-generativeai
    export GEMINI_API_KEY="your_key_here"

Run:
    python agent_demo.py
"""

import os
from regulations import REGULATIONS
from business_profile import get_business, SAMPLE_BUSINESSES
from rules_engine import evaluate_business, ALL_RULES

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Business the demo runs against (swap business_id to try others in SAMPLE_BUSINESSES)
ACTIVE_BUSINESS_ID = "B001"


# ---- Tools the agent can call ----
def search_regulations(keyword: str):
    """Search the regulatory knowledge base by keyword (matches any word in the phrase)."""
    words = keyword.lower().split()

    def score(reg):
        haystack = (reg["title"] + " " + reg["text"] + " " + reg["category"]).lower()
        return sum(haystack.count(w) for w in words)

    scored = sorted(REGULATIONS, key=score, reverse=True)
    return [r for r in scored if score(r) > 0][:3] or REGULATIONS[:1]


def query_business_data(business_id: str = ACTIVE_BUSINESS_ID):
    """Look up a business profile by ID (real lookup, no longer a hardcoded dict)."""
    biz = get_business(business_id)
    return biz.as_dict() if biz else {"error": f"No business found for id {business_id}"}


def check_requirement(requirement_name: str, business_id: str = ACTIVE_BUSINESS_ID):
    """
    Apply the rules engine to a business and return the finding matching
    requirement_name. Replaces the old inline threshold logic — this now
    calls the same rules_engine.py used standalone in rules_engine.py.
    """
    biz = get_business(business_id)
    if not biz:
        return {"error": f"No business found for id {business_id}"}

    requirement_name = requirement_name.lower()
    findings = evaluate_business(biz)
    for f in findings:
        if requirement_name in f.requirement.lower():
            return {"requirement": f.requirement, "applies": f.applies,
                     "reason": f.reason, "evidence_id": f.evidence_id}
    return {"requirement": requirement_name, "applies": None, "reason": "No matching rule found"}


TOOLS = {
    "search_regulations": search_regulations,
    "query_business_data": query_business_data,
    "check_requirement": check_requirement,
}


def run_agent_with_gemini(question):
    """Real agent loop using Gemini's native function calling."""
    import google.generativeai as genai
    genai.configure(api_key=GEMINI_API_KEY)

    model = genai.GenerativeModel(
        "gemini-2.5-flash",
        tools=[search_regulations, query_business_data, check_requirement],
    )
    chat = model.start_chat(enable_automatic_function_calling=True)
    response = chat.send_message(question)
    return response.text


def run_agent_mock(question):
    """
    Deterministic mock of the agent loop for environments without an API key —
    shows the SAME decide -> call -> use-result -> answer pattern the real
    Gemini function-calling loop follows. Now driven by the real rules engine
    instead of hardcoded threshold checks.
    """
    print("    Agent reasoning: question asks about registrations -> look up business profile first.")
    biz = query_business_data()
    print(f"    [tool_call] query_business_data() -> {biz}")

    print("    Agent reasoning: run the rules engine against every requirement it knows about.")
    biz_obj = get_business(ACTIVE_BUSINESS_ID)
    findings = evaluate_business(biz_obj)
    applicable = [f for f in findings if f.applies]
    for f in findings:
        print(f"    [tool_call] check_requirement('{f.requirement}') -> "
              f"applies={f.applies}, reason='{f.reason}'")

    print("    Agent reasoning: pull supporting regulatory evidence for each applicable finding.")
    lines = []
    for f in applicable:
        evidence = next((r for r in REGULATIONS if r["id"] == f.evidence_id), None)
        print(f"    [tool_call] search_regulations() -> matched evidence [{f.evidence_id}]")
        if evidence:
            lines.append(
                f"Finding: {f.requirement} applies.\n"
                f"  Reason: {f.reason}\n"
                f"  Evidence: [{evidence['id']}] {evidence['title']} ({evidence['source']})"
            )

    answer = "\n\n".join(lines)
    answer += (
        f"\n\nBusiness data used: turnover=Rs.{biz['turnover_lakh']}L, "
        f"employees={biz['employee_count']}, state={biz['state']}, "
        f"type={biz['business_type']}"
    )
    return answer


def main():
    print("=" * 70)
    print("SME COMPLIANCE ASSISTANT — AGENT (TOOL-CALLING) MINI-DEMO — Milestone 3")
    print("=" * 70)

    biz = get_business(ACTIVE_BUSINESS_ID)
    question = f"What registrations does {biz.name} need? Check the business profile and tell me."
    print(f"\nQuestion: {question}\n")

    if GEMINI_API_KEY:
        print("[Using live Gemini function calling]\n")
        answer = run_agent_with_gemini(question)
    else:
        print("[No GEMINI_API_KEY set — running deterministic mock of the same tool-calling pattern]\n")
        answer = run_agent_mock(question)

    print("\n" + "-" * 70)
    print("FINAL ANSWER:\n")
    print(answer)
    print("-" * 70)


if __name__ == "__main__":
    main()