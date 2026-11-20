import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { ActivityPoint, LanguageUsage } from '@/types'

const PALETTE = ['#8B5CF6', '#06B6D4', '#A78BFA', '#22C55E', '#F59E0B', '#EC4899', '#38BDF8', '#F472B6']

const tooltipStyle = {
  background: 'rgba(16,22,38,0.95)',
  border: '1px solid rgba(255,255,255,0.1)',
  borderRadius: 12,
  fontSize: 12,
  color: '#F8FAFC',
}

export function ActivityAreaChart({ data }: { data: ActivityPoint[] }) {
  const shaped = data.map((d) => ({
    label: (d.date ?? d.week ?? '').slice(5),
    words: d.words,
    transcriptions: d.transcriptions,
  }))
  return (
    <ResponsiveContainer width="100%" height={260}>
      <AreaChart data={shaped} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
        <defs>
          <linearGradient id="words" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#8B5CF6" stopOpacity={0.5} />
            <stop offset="100%" stopColor="#8B5CF6" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid stroke="rgba(148,163,184,0.10)" vertical={false} />
        <XAxis dataKey="label" tick={{ fill: '#64748B', fontSize: 11 }} axisLine={false} tickLine={false} />
        <YAxis tick={{ fill: '#64748B', fontSize: 11 }} axisLine={false} tickLine={false} />
        <Tooltip contentStyle={tooltipStyle} cursor={{ stroke: 'rgba(139,92,246,0.35)' }} />
        <Area type="monotone" dataKey="words" stroke="#8B5CF6" strokeWidth={2} fill="url(#words)" name="Words" />
      </AreaChart>
    </ResponsiveContainer>
  )
}

export function LanguagePieChart({ data }: { data: LanguageUsage[] }) {
  if (!data.length) return <p className="py-12 text-center text-xs text-ink-faint">No language data yet.</p>
  return (
    <ResponsiveContainer width="100%" height={260}>
      <PieChart>
        <Pie
          data={data}
          dataKey="count"
          nameKey="name"
          innerRadius={58}
          outerRadius={92}
          paddingAngle={2}
          stroke="rgba(8,11,20,0.6)"
        >
          {data.map((entry, i) => (
            <Cell key={entry.code} fill={PALETTE[i % PALETTE.length]} />
          ))}
        </Pie>
        <Tooltip contentStyle={tooltipStyle} />
        <Legend
          verticalAlign="bottom"
          height={36}
          formatter={(value) => <span style={{ color: '#94A3B8', fontSize: 11 }}>{value}</span>}
        />
      </PieChart>
    </ResponsiveContainer>
  )
}

export function ModelBarChart({ data }: { data: { name: string; count: number }[] }) {
  if (!data.length) return <p className="py-12 text-center text-xs text-ink-faint">No model usage recorded yet.</p>
  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={data} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
        <CartesianGrid stroke="rgba(148,163,184,0.10)" vertical={false} />
        <XAxis dataKey="name" tick={{ fill: '#64748B', fontSize: 10 }} axisLine={false} tickLine={false} interval={0} angle={-12} textAnchor="end" height={46} />
        <YAxis tick={{ fill: '#64748B', fontSize: 11 }} axisLine={false} tickLine={false} allowDecimals={false} />
        <Tooltip contentStyle={tooltipStyle} cursor={{ fill: 'rgba(139,92,246,0.08)' }} />
        <Bar dataKey="count" radius={[6, 6, 0, 0]} name="Transcriptions">
          {data.map((entry, i) => (
            <Cell key={entry.name} fill={PALETTE[i % PALETTE.length]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
