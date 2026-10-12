import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import Panel from "./Panel";
import "./barchartcard.css";

const AXIS_TICK = { fill: "var(--text-muted)", fontSize: 12 };

function ChartTooltip({ active, payload, label }) {
  if (!active || !payload || payload.length === 0) {
    return null;
  }

  return (
    <div className="chart-tooltip">
      <p className="chart-tooltip-label">{label}</p>
      <p className="chart-tooltip-value">{payload[0].value} tickets</p>
    </div>
  );
}

// A one-series bar chart in a panel. `data` is a list of { label, count }.
function BarChartCard({ title, subtitle, data }) {
  return (
    <Panel title={title} subtitle={subtitle}>
      {data.length === 0 ? (
        <p className="bar-chart-empty">No tickets yet.</p>
      ) : (
        <ResponsiveContainer width="100%" height={240}>
          <BarChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -20 }}>
            <CartesianGrid vertical={false} stroke="var(--grid)" />
            <XAxis dataKey="label" tick={AXIS_TICK} tickLine={false} axisLine={false} />
            <YAxis allowDecimals={false} tick={AXIS_TICK} tickLine={false} axisLine={false} />
            <Tooltip cursor={{ fill: "var(--hover)" }} content={<ChartTooltip />} />
            <Bar dataKey="count" fill="var(--series-1)" radius={[4, 4, 0, 0]} maxBarSize={40} isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer>
      )}
    </Panel>
  );
}

export default BarChartCard;
