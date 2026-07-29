import sys
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, LLM

# Same workarounds as classifier_agent.py / monitor_pipeline.py — same CrewAI/Groq bugs apply here.
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

import crewai.llms.cache as _crewai_cache
_crewai_cache.mark_cache_breakpoint = lambda message: dict(message)

load_dotenv()

from sparta_tool import SPARTAClassMappingTool, SPARTAIncidentSearchTool

llm = LLM(model="groq/llama-3.3-70b-versatile")

sparta_agent = Agent(
    role="SPARTA Analyst",
    goal="Explain a detected attack class in terms of the SPARTA threat taxonomy, grounded in the knowledge base",
    backstory=(
        "A space-security threat-intel specialist who maps detected anomalies to the "
        "SPARTA framework's tactics and techniques, and can cite real-world precedent."
    ),
    tools=[SPARTAClassMappingTool(), SPARTAIncidentSearchTool()],
    llm=llm,
    verbose=True,
)

if __name__ == "__main__":
    task = Task(
        description=(
            "The Classifier Agent detected 'Command Flooding' with confidence 0.96. "
            "Use get_sparta_class_mapping to look up its exact SPARTA tactic/technique "
            "mapping, then use search_sparta_incidents to find one related real-world "
            "precedent, then explain the threat in plain language citing both."
        ),
        expected_output="The SPARTA tactic ID, technique ID, a related real-world incident, and a plain-language threat explanation.",
        agent=sparta_agent,
    )
    crew = Crew(agents=[sparta_agent], tasks=[task], verbose=True)
    result = crew.kickoff()
    print(result)
