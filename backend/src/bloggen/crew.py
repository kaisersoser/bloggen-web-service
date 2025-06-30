from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai_tools import SerperDevTool, ScrapeWebsiteTool, WebsiteSearchTool
from pydantic import BaseModel, Field
import requests
from typing import List, Type
# If you want to run a snippet of code before or after the crew starts,
# you can use the @before_kickoff and @after_kickoff decorators
# https://docs.crewai.com/concepts/crews#example-crew-class-with-decorators

# 1. Define the input schema
class ScrapeWebsiteSchema(BaseModel):
    url: str = Field(..., description="The URL of the website to scrape")

# 2. Define your safe custom tool
class SafeScrapeWebsiteTool(ScrapeWebsiteTool):
    args_schema: Type[BaseModel] = ScrapeWebsiteSchema  # Required for Pydantic v2

    def _run(self, url: str) -> str:
        import requests

        try:
            response = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            content_type = response.headers.get("Content-Type", "").lower()

            # Allow only text or HTML content
            if not any(ct in content_type for ct in ["text/html", "text/plain"]):
                return f"[Skipped {url}: Unsupported content type: {content_type}]"

            # Optionally limit by content length (e.g., 1MB max)
            if int(response.headers.get("Content-Length", 0)) > 1_000_000:
                return f"[Skipped {url}: Content too large]"

            # return super()._run(url)
            return super()._run()

        except Exception as e:
            return f"[Error scraping {url}: {e}]"

@CrewBase
class Bloggen():
    """Bloggen crew"""

    agents: List[BaseAgent]
    tasks: List[Task]

    # Learn more about YAML configuration files here:
    # Agents: https://docs.crewai.com/concepts/agents#yaml-configuration-recommended
    # Tasks: https://docs.crewai.com/concepts/tasks#yaml-configuration-recommended
    
    # If you would like to add tools to your agents, you can learn more about it here:
    # https://docs.crewai.com/concepts/agents#agent-tools
    @agent
    def researcher(self) -> Agent:
        return Agent(
            config=self.agents_config['researcher'], # type: ignore[index]
            tools=[SerperDevTool(), SafeScrapeWebsiteTool()],
            llm="gpt-4o", # You can change this to any model you prefer
            verbose=True
        )

    @agent
    def content_creator(self) -> Agent:
        return Agent(
            config=self.agents_config['content_creator'], # type: ignore[index]
            verbose=True
        )

    @agent
    def fact_checker(self) -> Agent:
        return Agent(
            config=self.agents_config['fact_checker'], # type: ignore[index]
            tools=[SerperDevTool(), SafeScrapeWebsiteTool(), WebsiteSearchTool()],
            llm="gpt-4o",
            verbose=True
        )

    @agent
    def content_finalizer(self) -> Agent:
        return Agent(
            config=self.agents_config['content_finalizer'], # type: ignore[index]
            verbose=True
        )
        
        
    # To learn more about structured task outputs,
    # task dependencies, and task callbacks, check out the documentation:
    # https://docs.crewai.com/concepts/tasks#overview-of-a-task
    @task
    def research_task(self) -> Task:
        return Task(
            config=self.tasks_config['research_task'], # type: ignore[index]
            agent=self.researcher(),
        )

    @task
    def content_gen_task(self) -> Task:
        return Task(
            config=self.tasks_config['content_generation_task'], # type: ignore[index]
            agent=self.content_creator(),
        )

    @task
    def fact_checking_task(self) -> Task:
        return Task(
            config=self.tasks_config['fact_checking_task'], # type: ignore[index]
            agent=self.fact_checker(),
        )

    @task
    def content_finalization_task(self) -> Task:
        return Task(
            config=self.tasks_config['content_finalization_task'], # type: ignore[index]
            agent=self.content_finalizer(),
        )


    @crew
    def crew(self) -> Crew:
        """Creates the Bloggen crew"""
        # To learn how to add knowledge sources to your crew, check out the documentation:
        # https://docs.crewai.com/concepts/knowledge#what-is-knowledge

        return Crew(
            agents=self.agents, # Automatically created by the @agent decorator
            tasks=self.tasks, # Automatically created by the @task decorator
            process=Process.sequential,
            planning=True,
            verbose=True,
            # process=Process.hierarchical, # In case you wanna use that instead https://docs.crewai.com/how-to/Hierarchical/
        )
