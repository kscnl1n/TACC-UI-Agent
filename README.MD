Agent as a World 
================

This code was originally hosted on the Frontera system for private use by the Scalable Computational Intelligence group to develop frontend dashboards/websites for datasets. Hosted on the Frontera supercomputing cluster, input files (in the form of datasets, relevant site images, or other context)

**Ollama's qwen2.5-coder:14b model** is hosted locally on our systems, which is why we used this model specifically. If other LLMs are preferable, these can be downloaded locally and run through the command line with ollama--it just happened to be the best coding model we had on hand. 

Speed was an important consideration in this project and we were looking to optimize for it to avoid taking up compute time on Frontera, especially seeing as this was meant to be run in an interactive development environment. Thus, we chose Pydantic to organize schemas, validate handoffs between agents, and reject malformed outputs due to its speed.

**Pipeline steps**

The agent had to be able to perform these steps in sequence:
1. Read input files in from input_files
2. Inspect and summarize their contents for the LLM
3. Reason to create a sequential build plan
4. Generate frontend files for static website
5. Validate output
6. Reiterate and fix any mistakes/ensure app was runnable
7. Make web app runnable with npm command

**Overview**
```

                ┌──────────────────────────────┐
                │        User Prompt           │
                │  + input_files/ directory   │
                └──────────────┬──────────────┘
                               │
                               ▼
                ┌──────────────────────────────┐
                │     Supervisor Agent         │
                │ (Orchestrates everything)    │
                └──────────────┬──────────────┘
                               │
         ┌─────────────────────┴─────────────────────┐
         │                                           │
         ▼                                           ▼
┌──────────────────────┐                  ┌────────────────────────┐
│  Python Tools Layer  │                  │  FileAnalysisAgent     │
│ (deterministic)      │                  │  (LLM via LangChain)   │
└──────────┬───────────┘                  └──────────┬─────────────┘
           │                                         │
           ▼                                         ▼
┌──────────────────────────────┐        ┌──────────────────────────────┐
│ list_input_files()           │        │ Input: List[FileSummary]     │
│ summarize_csv()              │        │                              │
│ summarize_text()             │        │ Output: DatasetSummary       │
└──────────┬───────────────────┘        └──────────┬───────────────────┘
           │                                         │
           ▼                                         ▼
   ┌──────────────────────┐               ┌──────────────────────────────┐
   │ List[FileSummary]    │──────────────▶│ DatasetSummary                │
   └──────────────────────┘               └──────────┬───────────────────┘
                                                     │
                                                     ▼
                                      ┌──────────────────────────────┐
                                      │   AppPlanningAgent           │
                                      │   (LLM via LangChain)        │
                                      └──────────┬───────────────────┘
                                                 │
                                                 ▼
                                      ┌──────────────────────────────┐
                                      │ Input: DatasetSummary +      │
                                      │        User Prompt           │
                                      │ Output: AppPlan              │
                                      └──────────┬───────────────────┘
                                                 │
                                                 ▼
                                      ┌──────────────────────────────┐
                                      │ CodeGenerationAgent          │
                                      │ (LLM via LangChain)          │
                                      └──────────┬───────────────────┘
                                                 │
                                                 ▼
                                      ┌──────────────────────────────┐
                                      │ Input: AppPlan +             │
                                      │        DatasetSummary        │
                                      │ Output: GeneratedProject     │
                                      └──────────┬───────────────────┘
                                                 │
                                                 ▼
                                 ┌──────────────────────────────────────┐
                                 │ Python Tools Layer                   │
                                 │ (write + validate + finalize)        │
                                 └──────────┬───────────────────────────┘
                                            │
        ┌───────────────────────────────────┼──────────────────────────────────┐
        ▼                                   ▼                                  ▼
┌──────────────────────┐        ┌──────────────────────┐         ┌──────────────────────┐
│ write_generated_     │        │ copy_input_data_     │         │ validate_generated_  │
│ project()            │        │ to_public()          │         │ project()            │
└──────────┬───────────┘        └──────────┬───────────┘         └──────────┬───────────┘
           │                               │                                │
           ▼                               ▼                                ▼
   ┌──────────────────────┐        ┌──────────────────────┐        ┌──────────────────────┐
   │ generated_app/       │        │ public/data/         │        │ ValidationReport     │
   └──────────┬───────────┘        └──────────────────────┘        └──────────┬───────────┘
              │                                                             │
              ▼                                                             ▼
     ┌──────────────────────────────┐                          ┌──────────────────────────────┐
     │ JSON Artifacts Saved         │                          │ Final Output                 │
     │ dataset_summary.json         │                          │ Runnable React Dashboard     │
     │ app_plan.json                │                          │ (npm run dev)               │
     │ validation_report.json       │                          └──────────────────────────────┘
     └──────────────────────────────┘
```

**Running Pipeline**

This is a four-agent (Supervisor, file analysis, app planner, and code generator) system that utilizes Python scripts to handle coding tasks, Pydantic and Pandas to create agent schemas and clean and transform data respectively, React for website hosting on local machine whilst viewing output, and LLM agents to handle decision-making tasks such as website/dashboard design that would otherwise be left up to a human planner.

**Pipeline can be run by:**

pip install -r requirements.txt
ollama serve
ollama pull qwen2.5-coder:14b
bash run.sh "[PROMPT HERE]"

*Example prompts may include: 'Turn these input files as .csv data into a website dashboard', 'add these pictures of cats to a fake adoption website for the Houston SPCA', or 'Create a clean executive dashboard with KPI cards, revenue trends, and employee performance metrics using the .csv data attached. Use a minimal UI style'.*

**Site can be run in browser by:**

Run generated app with:
cd outputs/run_YYYY_MM_DD_HH_MM_SS/generated_app
npm install
npm run dev -- --host 0.0.0.0 --port [PORT OF CHOICE HERE (3000)]


It follows the systems messaging interface protocol with chain-of-thought for feedback loops. 

**What if I don't like my output?**

Try changing the prompts in prompts.py and running it again! They make it lean heavily towards dashboards.


**Future directions & Bugs**

Future directions for this project included extending capabilities for prompting by creating a web search tool so it can receieve information, and allowing the user to iterate and edit the produced codebases in real-time during idev sessions. Unfortunately, since I worked on it during the last month of my internship, this has been put on pause.
