from __future__ import annotations

import streamlit as st

from agents import InsuranceAgentSystem


COUNTIES_BY_STATE = {
    "TX": ["Dallas", "Harris", "Tarrant", "Bexar"],
    "FL": ["Miami-Dade"],
}

AGENT_EXPLANATIONS = [
    {
        "agent": "security_agent",
        "plain_english": "Checks the question before anything else. Blocks prompt injection, private client documents, credentials, and regulated advice requests.",
    },
    {
        "agent": "planner_agent",
        "plain_english": "Decides the workflow: search structured plan data, retrieve explanation documents, summarize the knowledge graph, then synthesize an answer.",
    },
    {
        "agent": "plan_search_agent",
        "plain_english": "Runs SQL-style search over public CMS plan data using state, county, metal level, and premium filters.",
    },
    {
        "agent": "retrieval_agent",
        "plain_english": "Finds relevant glossary/CMS explanation text using keyword search plus local vector-style retrieval.",
    },
    {
        "agent": "knowledge_graph_agent",
        "plain_english": "Summarizes relationships such as Plan -> Issuer, Plan -> Metal Level, Plan -> State, and Plan -> Service Area.",
    },
    {
        "agent": "answer_synthesis_agent",
        "plain_english": "Combines the structured plan facts and retrieved explanations into a beginner-friendly answer with citations.",
    },
]

METAL_LEVELS = [
    {
        "metal_level": "Bronze",
        "meaning": "Usually lower monthly premium, higher costs when care is used.",
    },
    {
        "metal_level": "Silver",
        "meaning": "Middle cost-sharing tier. Important because eligible users may get cost-sharing reductions on Silver plans.",
    },
    {
        "metal_level": "Gold",
        "meaning": "Usually higher monthly premium, lower costs when care is used.",
    },
    {
        "metal_level": "Platinum",
        "meaning": "Usually highest monthly premium, lowest costs when care is used.",
    },
]


@st.cache_resource
def load_agent_system() -> InsuranceAgentSystem:
    return InsuranceAgentSystem()


def escape_dollar_math(text: str) -> str:
    return text.replace("$", r"\$")


st.set_page_config(page_title="Insurance Copilot", layout="wide")
st.title("Insurance Copilot Agent MVP")

agent_system = load_agent_system()
summary = agent_system.summarize_graph()

col1, col2, col3 = st.columns(3)
col1.metric("Plans", f"{len(agent_system.copilot.plans_df):,}")
col2.metric("Graph nodes", f"{summary['nodes']:,}")
col3.metric("Graph edges", f"{summary['edges']:,}")

with st.expander("What this agent system actually does", expanded=True):
    st.write(
        "This is not one generic chatbot. It is a small multi-agent workflow. "
        "Each agent has one job, and the trace below shows which agents ran for the current question."
    )
    st.dataframe(AGENT_EXPLANATIONS, use_container_width=True, hide_index=True)

with st.expander("Insurance metal levels explained"):
    st.write(
        "Metal levels describe how costs are shared between the customer and the insurer. "
        "They are not quality ratings and do not mean doctors are better or worse."
    )
    st.dataframe(METAL_LEVELS, use_container_width=True, hide_index=True)

with st.sidebar:
    st.header("Filters")
    state = st.selectbox("State", ["", "TX", "FL"], index=1)
    county_options = [""] + COUNTIES_BY_STATE.get(state, [])
    default_county = "Dallas" if state == "TX" else ("Miami-Dade" if state == "FL" else "")
    county = st.selectbox("County", county_options, index=county_options.index(default_county))
    metal_level = st.selectbox("Metal level", ["", "Bronze", "Silver", "Gold", "Platinum"], index=2)
    max_premium = st.number_input("Max monthly premium", min_value=0.0, value=0.0, step=25.0)

question = st.text_area(
    "Ask a question",
    value="Find a silver plan in Dallas Texas and explain what deductible means.",
    height=100,
)

if st.button("Ask Copilot", type="primary"):
    if county and state and county not in COUNTIES_BY_STATE.get(state, []):
        st.error(f"{county} is not configured as a valid demo county for {state}. Pick a matching state/county pair.")
        st.stop()
    filters = {
        "state": state or None,
        "county": county or None,
        "metal_level": metal_level or None,
        "max_premium": max_premium if max_premium > 0 else None,
    }
    result = agent_system.ask(question, filters)
    st.subheader("Agent Trace")
    st.dataframe([step.__dict__ for step in result.trace], use_container_width=True)

    st.subheader("Security")
    st.write({"allowed": result.security.allowed, "reason": result.security.reason})

    st.subheader("Answer")
    st.markdown(escape_dollar_math(result.answer))

    st.subheader("Structured Plan Results")
    st.dataframe(result.plans, use_container_width=True)

    st.subheader("Knowledge Graph Relations")
    st.dataframe(
        [{"relation": relation, "edges": count} for relation, count in summary["top_relations"].items()],
        use_container_width=True,
    )

    st.subheader("Vector/RAG Documents")
    st.dataframe(result.retrieved_docs, use_container_width=True)

    st.subheader("Keyword Documents")
    st.dataframe(result.keyword_docs, use_container_width=True)
