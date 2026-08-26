"""
Agent Mini-Demo — SME Compliance Assistant
Pipeline: Question -> LLM decides tool -> Tool executes -> LLM uses result -> final answer

Setup:
    pip install google-generativeai
    export GEMINI_API_KEY="your_key_here"

Run:
    python agent_demo.py
"""

import os
import json
from regulations import REGULATIONS

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# ---- Mock business data (stands in for a real business-profile DB lookup) ----
BUSINESS_PROFILE = {
    "business_id": "B001",
    "name": "Sharma Textiles",
    "turnover_lakh": 50,
    "employee_count": 8,
    "state": "Madhya Pradesh",
    "registration_status": "unregistered",
}


# ---- Tools the agent can call ----
def search_regulations(keyword: str):
    """Search the regulatory knowledge base by keyword (matches any word in the phrase)."""
    words = keyword.lower().split()

    def score(reg):
        haystack = (reg["title"] + " " + reg["text"] + " " + reg["category"]).lower()
        return sum(haystack.count(w) for w in words)

    scored = sorted(REGULATIONS, key=score, reverse=True)
    return [r for r in scored if score(r) > 0][:3] or REGULATIONS[:1]


def query_business_data(field: str = None):
    """Return the current business profile (or a single field)."""
    if field and field in BUSINESS_PROFILE:
        return {field: BUSINESS_PROFILE[field]}
    return BUSINESS_PROFILE


def check_requirement(requirement_name: str, turnover_lakh: float, employee_count: int):
    """Apply a simple threshold rule to decide if a requirement applies."""
    requirement_name = requirement_name.lower()
    if "gst" in requirement_name:
        applies = turnover_lakh >= 40
        return {"requirement": "GST Registration", "applies": applies,
                "reason": f"Turnover Rs.{turnover_lakh}L vs Rs.40L threshold for goods"}
    if "shops" in requirement_name or "establishment" in requirement_name:
        applies = employee_count >= 1
        return {"requirement": "Shops & Establishments Registration", "applies": applies,
                "reason": f"Employs {employee_count} person(s); registration required once >=1"}
    if "pf" in requirement_name or "provident" in requirement_name:
        applies = employee_count >= 20
        return {"requirement": "PF Registration", "applies": applies,
                "reason": f"Employs {employee_count}; PF required only at >=20 employees"}
    return {"requirement": requirement_name, "applies": None, "reason": "No rule defined yet"}


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
    Gemini function-calling loop follows.
    """
    print("    Agent reasoning: question mentions turnover + employees -> check business data first.")
    biz = TOOLS["query_business_data"]()
    print(f"    [tool_call] query_business_data() -> {biz}")

    print("    Agent reasoning: now check GST applicability using that data.")
    gst_result = TOOLS["check_requirement"]("gst", biz["turnover_lakh"], biz["employee_count"])
    print(f"    [tool_call] check_requirement('gst', {biz['turnover_lakh']}, {biz['employee_count']}) -> {gst_result}")

    print("    Agent reasoning: also check Shops & Establishments since employees >= 1.")
    se_result = TOOLS["check_requirement"]("shops", biz["turnover_lakh"], biz["employee_count"])
    print(f"    [tool_call] check_requirement('shops', ...) -> {se_result}")

    print("    Agent reasoning: pull supporting regulatory evidence for the applicable findings.")
    gst_evidence = TOOLS["search_regulations"]("gst registration")
    se_evidence = TOOLS["search_regulations"]("shops establishment")
    print(f"    [tool_call] search_regulations('gst registration') -> {[r['id'] for r in gst_evidence]}")
    print(f"    [tool_call] search_regulations('shops establishment') -> {[r['id'] for r in se_evidence]}")

    answer = (
        f"Finding 1: GST Registration applies.\n"
        f"  Reason: {gst_result['reason']}\n"
        f"  Evidence: [{gst_evidence[0]['id']}] {gst_evidence[0]['title']} ({gst_evidence[0]['source']})\n\n"
        f"Finding 2: Shops & Establishments Registration applies.\n"
        f"  Reason: {se_result['reason']}\n"
        f"  Evidence: [{se_evidence[0]['id']}] {se_evidence[0]['title']} ({se_evidence[0]['source']})\n\n"
        f"Business data used: turnover=Rs.{biz['turnover_lakh']}L, employees={biz['employee_count']}, "
        f"state={biz['state']}"
    )
    return answer


def main():
    print("=" * 70)
    print("SME COMPLIANCE ASSISTANT — AGENT (TOOL-CALLING) MINI-DEMO")
    print("=" * 70)

    question = "What registrations does my business need? Check my profile and tell me."
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
