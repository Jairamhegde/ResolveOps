import { useState } from "react";
import { fetchUserDashboard, fetchUsers } from "../api";
import { useApi } from "../useApi";
import PageHeader from "../components/PageHeader";
import { Metric, MetricStrip } from "../components/Metrics";
import { ErrorMessage, Loading, Section } from "../components/Section";
import TicketTable from "../components/TicketTable";
import TicketDetails from "../components/TicketDetails";


function EmployeesPage({ token }) {
  const [pickedId, setPickedId] = useState("");
  const [selectedTicket, setSelectedTicket] = useState(null);

  const users = useApi(() => fetchUsers(token), [token]);
  const slackId = pickedId || users.data?.[0]?.slack_id || "";
  const dashboard = useApi(() => (slackId ? fetchUserDashboard(token, slackId) : Promise.resolve(null)), [token, slackId]);

  const employee = users.data?.find((user) => user.slack_id === slackId);
  const error = users.error || dashboard.error;

  return (
    <div className="page">
      <PageHeader
        title={employee ? employee.name : "Employees"}
        subtitle="The tickets one employee raised in Slack, and what happened to them"
        actions={
          users.data?.length > 0 && (
            <label className="field">
              Employee
              <select className="field-control" value={slackId} onChange={(event) => setPickedId(event.target.value)}>
                {users.data.map((user) => (
                  <option key={user.slack_id} value={user.slack_id}>
                    {user.name}
                  </option>
                ))}
              </select>
            </label>
          )
        }
      />

      {error && <ErrorMessage message={error} onRetry={users.error ? users.reload : dashboard.reload} />}
      {!error && (!users.data || (slackId && !dashboard.data)) && <Loading />}
      {users.data?.length === 0 && <p className="table-empty">No one has raised a ticket yet. Employees appear here after their first /helpdesk in Slack.</p>}

      {dashboard.data && (
        <div className={dashboard.loading ? "page-content is-loading" : "page-content"}>
          <MetricStrip label={`${employee?.name}'s tickets`}>
            <Metric label="Tickets raised" value={dashboard.data.metrics.total} detail="in Slack" />
            <Metric
              label="Solved"
              value={dashboard.data.metrics.resolved}
              detail={`${dashboard.data.metrics.solved_by_ai} by the AI, ${dashboard.data.metrics.solved_by_admin} by IT`}
            />
            <Metric
              label="Still open"
              value={dashboard.data.metrics.active + dashboard.data.metrics.pending_response}
              detail="not resolved yet"
            />
            <Metric
              label="High severity"
              value={dashboard.data.metrics.high_severity}
              detail={`${dashboard.data.metrics.high_severity_open} still open`}
              alert
            />
          </MetricStrip>

          <Section title="High-severity tickets" subtitle="Tickets the AI rated P1 or P2, with when they were raised" flush>
            <TicketTable
              tickets={dashboard.data.high_severity}
              onSelect={setSelectedTicket}
              selectedId={selectedTicket?.id}
              showReporter={false}
              emptyMessage="None of this employee's tickets were rated P1 or P2."
            />
          </Section>

          <Section title="All tickets" subtitle="Newest first" flush>
            <TicketTable
              tickets={dashboard.data.tickets}
              onSelect={setSelectedTicket}
              selectedId={selectedTicket?.id}
              showReporter={false}
              emptyMessage="This employee hasn't raised a ticket you can see."
            />
          </Section>
        </div>
      )}

      {selectedTicket && <TicketDetails ticket={selectedTicket} onClose={() => setSelectedTicket(null)} />}
    </div>
  );
}

export default EmployeesPage;
