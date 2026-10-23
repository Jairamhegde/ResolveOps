import { useState } from "react";
import { fetchSummary, fetchTickets } from "../api";
import { useApi } from "../useApi";
import { PRIORITIES, categoryLabel, isHighSeverity } from "../format";
import PageHeader from "../components/PageHeader";
import CategoryPicker from "../components/CategoryPicker";
import { Metric, MetricStrip } from "../components/Metrics";
import { BarList, DayChart, StatusBreakdown } from "../components/Charts";
import { ErrorMessage, Loading, Section } from "../components/Section";
import TicketTable from "../components/TicketTable";
import TicketDetails from "../components/TicketDetails";

const REFRESH_EVERY_MS = 30000;

// Most urgent first, then newest first.
function byUrgency(a, b) {
  return a.priority - b.priority || new Date(b.created_at) - new Date(a.created_at);
}

// The headline numbers, charts and the high-severity tickets still open.
// A category admin only ever sees their own category; a super admin can pick one or see all.
function OverviewPage({ token, isSuperAdmin }) {
  const [category, setCategory] = useState("");
  const [selectedTicket, setSelectedTicket] = useState(null);

  const summary = useApi(() => fetchSummary(token, category), [token, category], REFRESH_EVERY_MS);
  const tickets = useApi(() => fetchTickets(token, category), [token, category], REFRESH_EVERY_MS);

  const scopeCategory = summary.data?.category;
  const subtitle = scopeCategory ? `${categoryLabel(scopeCategory)} tickets only` : "Every ticket raised in Slack";

  return (
    <div className="page">
      <PageHeader
        title="Overview"
        subtitle={subtitle}
        actions={isSuperAdmin && <CategoryPicker value={category} onChange={setCategory} />}
      />

      {summary.error && <ErrorMessage message={summary.error} onRetry={summary.reload} />}
      {!summary.data && !summary.error && <Loading />}

      {summary.data && <Summary summary={summary.data} showCategories={!scopeCategory} />}

      {tickets.data && (
        <Section
          title="High severity, still open"
          subtitle="P1 and P2 tickets nobody has resolved yet, most urgent first"
          flush
        >
          <TicketTable
            tickets={tickets.data.filter((ticket) => isHighSeverity(ticket) && ticket.status !== "resolved").sort(byUrgency)}
            onSelect={setSelectedTicket}
            selectedId={selectedTicket?.id}
            emptyMessage="No open P1 or P2 tickets. Nothing urgent is waiting."
          />
        </Section>
      )}

      {selectedTicket && <TicketDetails ticket={selectedTicket} onClose={() => setSelectedTicket(null)} />}
    </div>
  );
}

function Summary({ summary, showCategories }) {
  const { metrics } = summary;
  const openCount = metrics.active + metrics.pending_response;

  return (
    <>
      <MetricStrip label="Ticket metrics">
        <Metric
          label="AI deflection rate"
          value={`${metrics.deflection_rate}%`}
          detail={`${metrics.solved_by_ai} of ${metrics.total} fixed with no admin`}
          ai
        />
        <Metric label="Total raised" value={metrics.total} detail="all time" />
        <Metric
          label="Active"
          value={openCount}
          detail={`${metrics.active} with IT, ${metrics.pending_response} waiting on employee`}
        />
        <Metric
          label="Closed"
          value={metrics.resolved}
          detail={`${metrics.solved_by_admin} by IT, ${metrics.solved_by_ai} by the AI`}
        />
        <Metric
          label="High severity open"
          value={metrics.high_severity_open}
          detail={`of ${metrics.high_severity} P1–P2 tickets`}
          alert
        />
        <Metric label="Needs review" value={metrics.needs_review} detail="held by the AI guard" alert />
      </MetricStrip>

      <Section title="Where tickets stand" subtitle="Every ticket by who fixed it, or who it's waiting on">
        <StatusBreakdown metrics={metrics} />
      </Section>

      <div className="section-grid">
        <Section title="Raised per day" subtitle="The last 14 days, in UTC">
          <DayChart days={summary.by_day} />
        </Section>

        <Section title="By priority" subtitle="P1 is the most urgent">
          <BarList
            rows={summary.by_priority.map((row) => ({ label: `P${row.priority} ${PRIORITIES[row.priority].label}`, count: row.count }))}
          />
        </Section>

        {showCategories && (
          <Section title="By category" subtitle="How the AI classified each issue">
            <BarList rows={summary.by_category.map((row) => ({ label: categoryLabel(row.category), count: row.count }))} />
          </Section>
        )}
      </div>
    </>
  );
}

export default OverviewPage;
