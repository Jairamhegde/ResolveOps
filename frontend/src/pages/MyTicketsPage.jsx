import { useState } from "react";
import { fetchMyTickets } from "../api";
import { useApi } from "../useApi";
import { PRIORITIES } from "../format";
import PageHeader from "../components/PageHeader";
import { Metric, MetricStrip } from "../components/Metrics";
import { BarList } from "../components/Charts";
import { ErrorMessage, Loading, Section } from "../components/Section";
import TicketTable from "../components/TicketTable";
import TicketDetails from "../components/TicketDetails";
import TopBar from "../components/TopBar";
import "./myticketspage.css";

function MyTicketsPage({ token, session, onLogOut }) {
  const [selectedTicket, setSelectedTicket] = useState(null);
  const mine = useApi(() => fetchMyTickets(token), [token], 30000);

  return (
    <div className="employee-app">
      <TopBar session={session} onLogOut={onLogOut} />

      <main className="page employee-page" id="content">
        <PageHeader title="My tickets" subtitle="Everything you raised with /helpdesk in Slack, and what happened to it" />

        {mine.error && <ErrorMessage message={mine.error} onRetry={mine.reload} />}
        {!mine.data && !mine.error && <Loading />}
        {mine.data && <MyTickets data={mine.data} selectedId={selectedTicket?.id} onSelect={setSelectedTicket} />}
      </main>

      {selectedTicket && <TicketDetails ticket={selectedTicket} onClose={() => setSelectedTicket(null)} />}
    </div>
  );
}

function MyTickets({ data, selectedId, onSelect }) {
  const { metrics } = data;

  return (
    <>
      <MetricStrip label="Your tickets">
        <Metric label="Total tickets" value={metrics.total} detail="submitted in Slack" />
        <Metric
          label="Solved"
          value={metrics.resolved}
          detail={`${metrics.solved_by_ai} by the AI's fix, ${metrics.solved_by_admin} by IT`}
          ai={metrics.solved_by_ai > 0}
        />
        <Metric
          label="Still open"
          value={metrics.active + metrics.pending_response}
          detail={metrics.pending_response ? `${metrics.pending_response} waiting for you to try a fix` : "being handled by IT"}
        />
        <Metric label="High priority" value={metrics.high_severity} detail="rated P1 or P2" />
      </MetricStrip>

      <div className="my-tickets-grid">
        <Section title="Priority of your tickets" subtitle="How urgent the AI rated each one. P1 is the most urgent.">
          <BarList rows={data.by_priority.map((row) => ({ label: `P${row.priority} ${PRIORITIES[row.priority].label}`, count: row.count }))} />
        </Section>

        <Section title="All tickets you submitted" subtitle="Newest first. Click a ticket to see the AI's suggested fix." flush>
          <TicketTable
            tickets={data.tickets}
            onSelect={onSelect}
            selectedId={selectedId}
            showReporter={false}
            emptyMessage="You haven't raised any tickets yet. Type /helpdesk and describe the problem in Slack."
          />
        </Section>
      </div>
    </>
  );
}

export default MyTicketsPage;
