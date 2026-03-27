
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List

# framework imports
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from pydantic import ValidationError

from models import AppPlan, DatasetSummary, FileSummary, GeneratedProject
from prompts import APP_PLANNING_PROMPT, CODE_GENERATION_PROMPT, FILE_ANALYSIS_PROMPT


# tools from tools.py 
from tools import (
    build_project_fallback,
    copy_input_data_to_public,
    create_run_directory,
    fallback_dataset_summary,
    list_input_files,
    summarize_csv,
    summarize_text,
    validate_generated_project,
    write_generated_project,
    write_json,
)


# simple base class for custom agents below:
class BaseAgent:
    def __init__(self, model: ChatOllama):
        self.model = model



'''
Error somewhere in here with dashboard gen 10/21/2026
'''

'''
CUSTOM AGENTS
View 'prompts.py' for comprehensive overview of what each agent does.
'''

# Custom agent 1: file analysis

class FileAnalysisAgent(BaseAgent):
    def run(self, file_summaries: List[FileSummary]) -> DatasetSummary:
        structured = self.model.with_structured_output(DatasetSummary)
        content = {
            "file_summaries": [fs.model_dump() for fs in file_summaries]
        }
        try:
            return structured.invoke([
                SystemMessage(content=FILE_ANALYSIS_PROMPT),
                HumanMessage(content=str(content)),
            ])
        except Exception:
            return fallback_dataset_summary(file_summaries)




# Custom agent 2: app planning/UI planning
# This agent specifically does an extremely important task: it substitutes the human decision-making process for
# designing and arranging the website.

class AppPlanningAgent(BaseAgent):
    def run(self, user_prompt: str, dataset_summary: DatasetSummary) -> AppPlan:
        structured = self.model.with_structured_output(AppPlan)
        content = {
            "user_prompt": user_prompt,
            "dataset_summary": dataset_summary.model_dump(),
        }
        try:
            return structured.invoke([
                SystemMessage(content=APP_PLANNING_PROMPT),
                HumanMessage(content=str(content)),
            ])
        
        # if planning fails, manually construct a basic fallback app plan:
        except Exception as exc:
            return AppPlan(
                pages=["Dashboard"],
                key_metrics=dataset_summary.suggested_metrics[:4] or ["Total Records", "Total Files"],
                filters=["data source"],
                design_notes=[f"Fallback plan used because planning agent failed: {exc}"],
            )

# Custom agent 3: code generation
# This agent is responsible for actually generating the code.
# input - appPlan and dataset summary, output: generated project

class CodeGenerationAgent(BaseAgent):
    def run(self, app_plan: AppPlan, dataset_summary: DatasetSummary) -> GeneratedProject:
        structured = self.model.with_structured_output(GeneratedProject)
        content = {
            "app_plan": app_plan.model_dump(),
            "dataset_summary": dataset_summary.model_dump(),
        }
        try:
            return structured.invoke([
                SystemMessage(content=CODE_GENERATION_PROMPT),
                HumanMessage(content=str(content)),
            ])
        
        # fallback - use dterministic project builder if model generation does not work
        except Exception:
            return build_project_fallback(dataset_summary, app_plan)


# Custom agent 4: our supervisor to manage the 3 worker agent.

class SupervisorAgent:

    # This class owns the model and orchestrates between agents.

    # initialize LLM - you may change the temperature here
    def __init__(self, model_name: str, temperature: float = 0.1, base_url: str = "http://127.0.0.1:11434"):
        # the actual langchain model that talks to ollama
        self.model = ChatOllama(model=model_name, temperature=temperature, base_url=base_url)
        # define agents:
        self.file_analysis_agent = FileAnalysisAgent(self.model)
        self.app_planning_agent = AppPlanningAgent(self.model)
        self.code_generation_agent = CodeGenerationAgent(self.model)

    # Private helper method to inspect the input directory and build a list of FileSummary objects,
    # which are a structured summary of each input file - we do this so we're not just
    # handing raw data to our LLM 
    def _summarize_input_files(self, input_dir: Path) -> List[FileSummary]:
        summaries: List[FileSummary] = []
        for path in list_input_files(input_dir):
            suffix = path.suffix.lower()
            if suffix == ".csv":
                summaries.append(summarize_csv(path))
            elif suffix in {".txt", ".md", ".json"}:
                summaries.append(summarize_text(path))
            else:
                summaries.append(FileSummary(
                    path=str(path),
                    name=path.name,
                    file_type="unknown",
                    summary="Unsupported file type. The planner may choose to ignore it.",
                ))
        return summaries # as JSON objects

    def run(self, user_prompt: str, input_dir: Path, outputs_dir: Path) -> Path:
        run_dir = create_run_directory(outputs_dir)
        app_dir = run_dir / "generated_app"

        file_summaries = self._summarize_input_files(input_dir)
        dataset_summary = self.file_analysis_agent.run(file_summaries)
        app_plan = self.app_planning_agent.run(user_prompt, dataset_summary)
        project = self.code_generation_agent.run(app_plan, dataset_summary)

        write_generated_project(project, app_dir)
        copy_input_data_to_public(input_dir, app_dir)
        report = validate_generated_project(app_dir)

        write_json(run_dir / "dataset_summary.json", dataset_summary.model_dump())
        write_json(run_dir / "app_plan.json", app_plan.model_dump())
        write_json(run_dir / "validation_report.json", report.model_dump())

        return run_dir

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="generate a React dashboard from files in ./input_files")
    parser.add_argument(
        "--prompt",
        required=True,
        help="user prompt describing the desired dashboard, e.g. 'Turn these input files into a website dashboard.'",
    )

    
    parser.add_argument("--input-dir", default="input_files", help="directory containing input data files.")
    parser.add_argument("--outputs-dir", default="outputs", help="directory where generated runs will be stored.")
    parser.add_argument("--model", default="qwen2.5-coder:14b", help="Ollama model name.")
    parser.add_argument("--base-url", default="http://127.0.0.1:11434", help="Ollama base URL.")
    return parser.parse_args()



def main() -> int:
    args = parse_args()
    input_dir = Path(args.input_dir)
    outputs_dir = Path(args.outputs_dir)

    supervisor = SupervisorAgent(model_name=args.model, base_url=args.base_url)
    run_dir = supervisor.run(args.prompt, input_dir, outputs_dir)

    print(f"Run completed successfully! {run_dir}")
    print(f"Generated app output here: {run_dir / 'generated_app'}")
    print("To run the generated dashboard locally, type in commands:")
    print(f"  cd {run_dir / 'generated_app'}")
    print("  npm install")
    print("  npm run dev -- --host 0.0.0.0 --port [PORT OF CHOICE (3000 recommended)]")
    return 0






if __name__ == "__main__":
    raise SystemExit(main())
