import { useEffect, useMemo, useState } from 'react';
import Papa from 'papaparse';
import KpiCard from './components/KpiCard';
import type { Dataset, Row } from './types';

const files = ["adoptions.csv", "employees.csv"];

async function loadCsv(fileName: string): Promise<Dataset> {
  const response = await fetch(`/data/${fileName}`);
  const text = await response.text();
  const parsed = Papa.parse<Row>(text, { header: true, skipEmptyLines: true });
  const rows = parsed.data;
  const columns = rows.length > 0 ? Object.keys(rows[0]) : [];
  return { fileName, rows, columns };
}

export default function App() {
  const [datasets, setDatasets] = useState<Dataset[]>([]);

  useEffect(() => {
    Promise.all(files.map(loadCsv)).then(setDatasets);
  }, []);

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
        <KpiCard label="hours_worked" value={totalFiles} />
        <KpiCard label="revenue" value={totalRows} />
        <KpiCard label="tasks_completed" value={totalColumns} />
      </section>

      <section className='stack'>
        {datasets.map((dataset) => (
          <div className='card' key={dataset.fileName}>
            <h2>{dataset.fileName}</h2>
            <p className='muted'>Rows: {dataset.rows.length} | Columns: {dataset.columns.join(', ') || 'None'}</p>
            <div className='table-wrap'>
              <table>
                <thead>
                  <tr>
                    {dataset.columns.map((column) => <th key={column}>{column}</th> )}
                  </tr>
                </thead>
                <tbody>
                  {dataset.rows.slice(0, 5).map((row, idx) => (
                    <tr key={idx}>
                      {dataset.columns.map((column) => <td key={column}>{row[column] ?? ''}</td>)}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ))}
      </section>
    </div>
  );
}
