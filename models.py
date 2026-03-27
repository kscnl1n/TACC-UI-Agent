'''
This is the data contract file. It defines schemas for:
- what one input file looks like after summarization
- what the whole dataset looks like after analysis
- what the app plan looks like
- what one generated file looks like
- what the final generated project looks like
- what validation results look like.

and a few related response objects.

Feel free to tinker with this in a local version if you would like different outputs,
but please do not change any code on the master version in /SambaNova_Agent. Be aware that any changes you make here
will have massive consequences upstream.

'''

# Import future for type hints
from __future__ import annotations

from typing import Dict, List, Literal, Optional
# Import pydantic for schema support
from pydantic import BaseModel, Field

# Restrict file types to a known set so the system doesn’t invent unexpected values
FileType = Literal["csv", "json", "txt", "md", "unknown"]
# Restrict chart types so the planner and generator stay within supported visualizations
ChartType = Literal["line", "bar", "pie", "area", "table", "kpi"]
FrameworkType = Literal["react-vite"]
LanguageType = Literal["typescript"]



'''
JSON summaries for objects
'''


class FileSummary(BaseModel):
    '''
    Structured summary of one input file.

    This is the bridge between raw data (CSV, text, etc.)
    and the LLM. Instead of passing full files, we pass a compact
    description that is easier for the model to work with.
    '''
    path: str
    name: str
    file_type: FileType
    rows: Optional[int] = None
    columns: List[str] = Field(default_factory=list)
    # A small preview of the data (helps the model understand content without large inputs, crucial for speed)
    sample_rows: List[Dict[str, str]] = Field(default_factory=list)
    summary: str

class DatasetSummary(BaseModel):
    '''
    High-level understanding of all input files together.
    Reports what datasets exist and how they likely connect.
    '''
    files: List[FileSummary]
    entities: List[str] = Field(default_factory=list)
    likely_relationships: List[str] = Field(default_factory=list)
    suggested_metrics: List[str] = Field(default_factory=list)
    caveats: List[str] = Field(default_factory=list)
    combined_summary: str


class ChartSpec(BaseModel):
    '''
    Describes one chart in the output.
    '''
    title: str
    chart_type: ChartType
    x: Optional[str] = None
    y: Optional[str] = None
    group_by: Optional[str] = None
    description: str


class AppPlan(BaseModel):
    '''
    Blueprint for the frontend application.
    '''
    
    app_name: str = "generated-dashboard"
    framework: FrameworkType = "react-vite" # You can change this if another framework is preferred, but there is no guarantee the npm commands will still work.
    language: LanguageType = "typescript" # This is the programming language for the dashboard/webpage/frontend - Typescript is chosen here for standardization purposes but it may be edited if desired.
    pages: List[str] = Field(default_factory=lambda: ["Dashboard"])
    charts: List[ChartSpec] = Field(default_factory=list)
    filters: List[str] = Field(default_factory=list)
    key_metrics: List[str] = Field(default_factory=list)
    design_notes: List[str] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=lambda: ["react", "react-dom", "papaparse", "recharts"])
    run_command: str = "npm install && npm run dev"


# Class for single generated file
class GeneratedFile(BaseModel):
    path: str
    content: str

# Class for single generated project
class GeneratedProject(BaseModel):
    files: List[GeneratedFile]
    explanation: str

# Class for validation report for the success of the project as a whole 
class ValidationReport(BaseModel):
    ok: bool
    missing_files: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
