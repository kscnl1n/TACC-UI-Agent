type Props = { label: string; value: string | number };

export default function KpiCard({ label, value }: Props) {
  return (
    <div className='card'>
      <div className='muted'>{label}</div>
      <div className='kpi'>{value}</div>
    </div>
  );
}
