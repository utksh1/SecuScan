import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { useEffect, useMemo, useState } from 'react'

const vulnerabilityTrend = [
  { day: 'Mon', critical: 4, high: 9, medium: 18 },
  { day: 'Tue', critical: 6, high: 12, medium: 21 },
  { day: 'Wed', critical: 3, high: 10, medium: 16 },
  { day: 'Thu', critical: 8, high: 14, medium: 24 },
  { day: 'Fri', critical: 5, high: 11, medium: 19 },
   { day: 'Sat', critical: 7, high: 13, medium: 22 },
  { day: 'Sun', critical: 4, high: 8, medium: 15 },
]

const severityData = [
  { name: 'Critical', value: 18 },
  { name: 'High', value: 42 },
  { name: 'Medium', value: 76 },
  { name: 'Low', value: 55 },
]

const targetRisk = [
  { target: 'api.secuscan.local', risk: 94 },
  { target: 'admin.panel', risk: 87 },
  { target: 'auth.gateway', risk: 72 },
  { target: 'cdn.edge', risk: 51 },
]

const scanStats = [
  { name: 'Success', value: 72 },
  { name: 'Failed', value: 18 },
  { name: 'Aborted', value: 10 },
]

const COLORS = ['#ef4444', '#f97316', '#eab308', '#22c55e']

function MetricCard({ label, value, detail }: { label: string; value: string; detail: string }) {
  return (
    <div className="bg-charcoal border-4 border-black p-6 shadow-[6px_6px_0px_0px_rgba(0,0,0,1)]">
      <p className="text-[10px] font-black uppercase tracking-[0.25em] text-silver/40">{label}</p>
      <p className="mt-4 text-4xl font-black text-silver-bright">{value}</p>
      <p className="mt-2 text-[10px] font-mono uppercase tracking-widest text-silver/30">{detail}</p>
    </div>
  )
}

function ChartCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="bg-charcoal border-4 border-black p-6 shadow-[8px_8px_0px_0px_rgba(0,0,0,1)]">
      <h2 className="mb-6 text-xs font-black uppercase tracking-[0.25em] text-silver-bright">
        {title}
      </h2>
      <div className="h-72">{children}</div>
    </section>
  )
}
export default function Analytics() {

  const [timeRange, setTimeRange] = useState<'7d' | '30d' | '90d'>('7d')
  const [lastUpdated, setLastUpdated] = useState(new Date())

  useEffect(() => {
    const interval = window.setInterval(() => {
      setLastUpdated(new Date())
    }, 30000)

    return () => window.clearInterval(interval)
  }, [])

  const filteredTrend = useMemo(() => {
    if (timeRange === '7d') return vulnerabilityTrend.slice(-7)
    if (timeRange === '30d') return vulnerabilityTrend
    return vulnerabilityTrend
  }, [timeRange])

  return (
    <div className="min-h-screen bg-charcoal-dark text-silver p-6 md:p-12 pb-32 space-y-10">
      <header className="border-b-4 border-silver-bright/10 pb-10">
        <div className="bg-rag-blue text-black px-4 py-1 text-xs uppercase tracking-widest inline-block font-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
          Analytics_Core v1.0
        </div>

        <h1 className="mt-5 text-5xl md:text-7xl font-black uppercase italic tracking-tighter text-silver-bright">
          Security Analytics
        </h1>

      <p className="mt-4 text-xs font-mono uppercase tracking-widest text-silver/40">
  Vulnerability trends // scan statistics // target risk analysis
</p>

<div className="mt-6 flex flex-wrap gap-3">
  {(['7d', '30d', '90d'] as const).map((range) => (
    <button
      key={range}
      onClick={() => setTimeRange(range)}
      className={`border-4 border-black px-4 py-2 text-xs font-black uppercase ${
        timeRange === range
          ? 'bg-rag-blue text-black'
          : 'bg-charcoal text-silver'
      }`}
    >
      {range}
    </button>
  ))}
</div>

<p className="mt-3 text-[10px] font-mono uppercase tracking-widest text-silver/40">
  Auto refresh enabled // Last updated: {lastUpdated.toLocaleTimeString()}
</p>

</header>

     <section className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-6">
        <MetricCard label="Total Vulnerabilities" value="191" detail="+12 this week" />
        <MetricCard label="Critical Findings" value="18" detail="Immediate action" />
        <MetricCard label="Scan Success Rate" value="72%" detail="Last 30 days" />
        <MetricCard label="High Risk Targets" value="04" detail="Ranked by exposure" />
      </section>

      <section className="grid grid-cols-1 xl:grid-cols-2 gap-8">
        <ChartCard title="Vulnerabilities Over Time">
        <ResponsiveContainer width="100%" height="100%">
  <LineChart data={filteredTrend}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="day" />
              <YAxis />
              <Tooltip />
              <Line type="monotone" dataKey="critical" stroke="#ef4444" strokeWidth={3} />
              <Line type="monotone" dataKey="high" stroke="#f97316" strokeWidth={3} />
              <Line type="monotone" dataKey="medium" stroke="#eab308" strokeWidth={3} />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Severity Distribution">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie data={severityData} dataKey="value" nameKey="name" outerRadius={95} label>
                {severityData.map((_, index) => (
                  <Cell key={index} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Most Vulnerable Targets">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={targetRisk}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="target" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="risk" fill="#38bdf8" />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Scan Success vs Failure">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie data={scanStats} dataKey="value" nameKey="name" outerRadius={95} label>
                {scanStats.map((_, index) => (
                  <Cell key={index} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </ChartCard>
      </section>
    </div>
  )
}