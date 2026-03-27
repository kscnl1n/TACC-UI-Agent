from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import List

import pandas as pd

from models import DatasetSummary, FileSummary, GeneratedProject, ValidationReport


SUPPORTED_TEXT_SUFFIXES = {'.txt', '.md', '.json'}

# Scan directory and list all files inside
def list_input_files(input_dir: Path) -> List[Path]:
    if not input_dir.exists():
        raise FileNotFoundError(f'Input directory does not exist: {input_dir}')
    return sorted([p for p in input_dir.iterdir() if p.is_file()])

# Read csv file and convert it into FileSummary *used in FileSummary
def summarize_csv(path: Path, sample_rows: int = 5) -> FileSummary:
    df = pd.read_csv(path)
    preview = df.head(sample_rows).fillna('')
    return FileSummary(
        path=str(path),
        name=path.name,
        file_type='csv',
        rows=int(len(df)),
        columns=[str(c) for c in df.columns.tolist()],
        sample_rows=preview.astype(str).to_dict(orient='records'),
        summary=f'CSV file with {len(df)} rows and {len(df.columns)} columns.',
    )

# Take a peek at a file and summarize its contents in text
def summarize_text(path: Path, max_chars: int = 2500) -> FileSummary:
    text = path.read_text(encoding='utf-8', errors='ignore')
    trimmed = text[:max_chars]
    suffix = path.suffix.lower()
    file_type = 'json' if suffix == '.json' else 'md' if suffix == '.md' else 'txt'
    return FileSummary(
        path=str(path),
        name=path.name,
        file_type=file_type,
        summary=f'Text-like file preview: {trimmed}',
    )

# Creates a new timestamped folder for each run (to keep track of different versions of generated code)
def fallback_dataset_summary(file_summaries: List[FileSummary]) -> DatasetSummary:
    csv_columns: list[str] = []
    for fs in file_summaries:
        if fs.columns:
            csv_columns.extend(fs.columns)
    unique_columns = sorted(set(csv_columns))
    metrics = [
        c
        for c in unique_columns
        if any(token in c.lower() for token in ['sales', 'revenue', 'amount', 'hours', 'task', 'count', 'total'])
    ]
    return DatasetSummary(
        files=file_summaries,
        entities=['records', 'employees'] if unique_columns else ['records'],
        likely_relationships=['Possible joins may exist across similarly named identifier columns.'],
        suggested_metrics=metrics[:8],
        caveats=['This dataset summary was produced by deterministic fallback logic because the model step failed.'],
        combined_summary='Dataset contains the files discovered in the input directory and can support a basic dashboard.',
    )

# Creates the run directory with above timestamp ^
def create_run_directory(outputs_dir: Path) -> Path:
    outputs_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime('run_%Y_%m_%d_%H_%M_%S')
    run_dir = outputs_dir / timestamp
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir

# Copies input files into the frontend app’s public folder
def copy_input_data_to_public(input_dir: Path, app_dir: Path) -> None:
    public_data_dir = app_dir / 'public' / 'data'
    public_data_dir.mkdir(parents=True, exist_ok=True)
    for path in list_input_files(input_dir):
        shutil.copy2(path, public_data_dir / path.name)

# Writes structured data (like summaries or plans) to a JSON file
def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding='utf-8')

# Stores generated code into actual projects
def write_generated_project(project: GeneratedProject, app_dir: Path) -> None:
    app_dir.mkdir(parents=True, exist_ok=True)
    for item in project.files:
        target = app_dir / item.path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(item.content, encoding='utf-8')

# Ensures required files for building are in the project
def validate_generated_project(app_dir: Path) -> ValidationReport:
    required = [
        'package.json',
        'tsconfig.json',
        'vite.config.ts',
        'index.html',
        'src/main.tsx',
        'src/App.tsx',
        'src/types.ts',
    ]
    missing = [rel for rel in required if not (app_dir / rel).exists()]
    warnings: list[str] = []
    if not (app_dir / 'public' / 'data').exists():
        warnings.append('public/data directory is missing.')
    return ValidationReport(ok=len(missing) == 0, missing_files=missing, warnings=warnings)

# Fallback function to generate a dashboard without LLM help (python helper functions only)
def build_project_fallback(dataset_summary: DatasetSummary, app_plan) -> GeneratedProject:
    kpis = app_plan.key_metrics[:3] if getattr(app_plan, 'key_metrics', None) else ['Total Files', 'Total Rows', 'Unique Columns']
    csv_names = [fs.name for fs in dataset_summary.files if fs.file_type == 'csv']

    package_json = json.dumps(
        {
            'name': app_plan.app_name,
            'private': True,
            'version': '0.0.1',
            'type': 'module',
            'scripts': {'dev': 'vite', 'build': 'tsc && vite build', 'preview': 'vite preview'},
            'dependencies': {
                'papaparse': '^5.5.3',
                'react': '^18.3.1',
                'react-dom': '^18.3.1',
                'recharts': '^2.15.4',
            },
            'devDependencies': {
                '@types/papaparse': '^5.3.16',
                '@types/react': '^18.3.12',
                '@types/react-dom': '^18.3.1',
                '@vitejs/plugin-react': '^4.3.4',
                'typescript': '^5.6.3',
                'vite': '^5.4.10',
            },
        },
        indent=2,
    )

    tsconfig_json = json.dumps(
        {
            'compilerOptions': {
                'target': 'ES2020',
                'useDefineForClassFields': True,
                'lib': ['ES2020', 'DOM', 'DOM.Iterable'],
                'allowJs': False,
                'skipLibCheck': True,
                'esModuleInterop': True,
                'allowSyntheticDefaultImports': True,
                'strict': True,
                'forceConsistentCasingInFileNames': True,
                'module': 'ESNext',
                'moduleResolution': 'Node',
                'resolveJsonModule': True,
                'isolatedModules': True,
                'noEmit': True,
                'jsx': 'react-jsx',
            },
            'include': ['src'],
            'references': [],
        },
        indent=2,
    )

    app_tsx = f"""import {{ useEffect, useMemo, useState }} from 'react';
import Papa from 'papaparse';
import KpiCard from './components/KpiCard';
import type {{ Dataset, Row }} from './types';

const files = {json.dumps(csv_names)};

async function loadCsv(fileName: string): Promise<Dataset> {{
  const response = await fetch(`/data/${{fileName}}`);
  const text = await response.text();
  const parsed = Papa.parse<Row>(text, {{ header: true, skipEmptyLines: true }});
  const rows = parsed.data;
  const columns = rows.length > 0 ? Object.keys(rows[0]) : [];
  return {{ fileName, rows, columns }};
}}

export default function App() {{
  const [datasets, setDatasets] = useState<Dataset[]>([]);

  useEffect(() => {{
    Promise.all(files.map(loadCsv)).then(setDatasets);
  }}, []);

  const totalRows = useMemo(() => datasets.reduce((sum, ds) => sum + ds.rows.length, 0), [datasets]);
  const totalFiles = datasets.length;
  const totalColumns = useMemo(() => new Set(datasets.flatMap((ds) => ds.columns)).size, [datasets]);

  return (
    <div className='page'>
      <header className='hero'>
        <h1>Generated Dashboard</h1>
        <p>Basic fallback dashboard generated when the coding model could not provide a structured project.</p>
      </header>

      <section className='grid'>
        <KpiCard label={json.dumps(kpis[0] if len(kpis) > 0 else 'Total Files')} value={{totalFiles}} />
        <KpiCard label={json.dumps(kpis[1] if len(kpis) > 1 else 'Total Rows')} value={{totalRows}} />
        <KpiCard label={json.dumps(kpis[2] if len(kpis) > 2 else 'Unique Columns')} value={{totalColumns}} />
      </section>

      <section className='stack'>
        {{datasets.map((dataset) => (
          <div className='card' key={{dataset.fileName}}>
            <h2>{{dataset.fileName}}</h2>
            <p className='muted'>Rows: {{dataset.rows.length}} | Columns: {{dataset.columns.join(', ') || 'None'}}</p>
            <div className='table-wrap'>
              <table>
                <thead>
                  <tr>
                    {{dataset.columns.map((column) => <th key={{column}}>{{column}}</th> )}}
                  </tr>
                </thead>
                <tbody>
                  {{dataset.rows.slice(0, 5).map((row, idx) => (
                    <tr key={{idx}}>
                      {{dataset.columns.map((column) => <td key={{column}}>{{row[column] ?? ''}}</td>)}}
                    </tr>
                  ))}}
                </tbody>
              </table>
            </div>
          </div>
        ))}}
      </section>
    </div>
  );
}}
"""

    files = [
        {
            'path': 'package.json',
            'content': package_json,
        },
        {
            'path': 'tsconfig.json',
            'content': tsconfig_json,
        },
        {
            'path': 'vite.config.ts',
            'content': "import { defineConfig } from 'vite';\nimport react from '@vitejs/plugin-react';\n\nexport default defineConfig({ plugins: [react()] });\n",
        },
        {
            'path': 'index.html',
            'content': "<!doctype html>\n<html lang='en'>\n  <head>\n    <meta charset='UTF-8' />\n    <meta name='viewport' content='width=device-width, initial-scale=1.0' />\n    <title>Generated Dashboard</title>\n  </head>\n  <body>\n    <div id='root'></div>\n    <script type='module' src='/src/main.tsx'></script>\n  </body>\n</html>\n",
        },
        {
            'path': 'src/main.tsx',
            'content': "import React from 'react';\nimport ReactDOM from 'react-dom/client';\nimport App from './App';\nimport './styles.css';\n\nReactDOM.createRoot(document.getElementById('root')!).render(\n  <React.StrictMode>\n    <App />\n  </React.StrictMode>\n);\n",
        },
        {
            'path': 'src/types.ts',
            'content': "export type Row = Record<string, string>;\nexport type Dataset = { fileName: string; rows: Row[]; columns: string[] };\n",
        },
        {
            'path': 'src/components/KpiCard.tsx',
            'content': "type Props = { label: string; value: string | number };\n\nexport default function KpiCard({ label, value }: Props) {\n  return (\n    <div className='card'>\n      <div className='muted'>{label}</div>\n      <div className='kpi'>{value}</div>\n    </div>\n  );\n}\n",
        },
        {
            'path': 'src/App.tsx',
            'content': app_tsx,
        },
        {
            'path': 'src/styles.css',
            'content': ":root { font-family: Inter, system-ui, sans-serif; color: #111827; background: #f3f4f6; }\n* { box-sizing: border-box; }\nbody { margin: 0; }\n.page { max-width: 1200px; margin: 0 auto; padding: 2rem; }\n.hero { margin-bottom: 1.5rem; }\n.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 1rem; margin-bottom: 1.5rem; }\n.stack { display: grid; gap: 1rem; }\n.card { background: white; border-radius: 16px; padding: 1rem; box-shadow: 0 8px 24px rgba(0,0,0,0.06); }\n.kpi { font-size: 2rem; font-weight: 700; margin-top: 0.25rem; }\n.muted { color: #6b7280; }\n.table-wrap { overflow-x: auto; }\ntable { width: 100%; border-collapse: collapse; }\nth, td { text-align: left; padding: 0.5rem; border-bottom: 1px solid #e5e7eb; }\n",
        },
    ]
    return GeneratedProject(files=files, explanation='Fallback project generated without an LLM code response.')
