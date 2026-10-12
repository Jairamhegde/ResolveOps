import { useEffect, useState } from "react";
import { fetchOverview } from "./api";
import Navbar from "./components/Navbar";
import StatCard from "./components/StatCard";
import BarChartCard from "./components/BarChartCard";
import TicketList from "./components/TicketList";

const REFRESH_EVERY_MS = 10000;

// The API only returns priorities that have tickets, so fill the gaps to always show P1 to P5.
function toPriorityBars(byPriority) {
  return [1, 2, 3, 4, 5].map((priority) => {
    const row = byPriority.find((item) => item.priority === priority);
    return { label: `P${priority}`, count: row ? row.count : 0 };
  });
}

function toCategoryBars(byCategory) {
  return byCategory.map((row) => ({
    label: row.category ? row.category.replaceAll("_", " ") : "uncategorized",
    count: row.count,
  }));
}

function App() {
  const [overview, setOverview] = useState(null);
  const [updatedAt, setUpdatedAt] = useState(null);
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    function loadOverview() {
      fetchOverview()
        .then((data) => {
          setOverview(data);
          setUpdatedAt(new Date());
          setErrorMessage("");
        })
        .catch(() => setErrorMessage("Could not load the dashboard. Is the backend running?"));
    }

    loadOverview();
    const timer = setInterval(loadOverview, REFRESH_EVERY_MS);
    return () => clearInterval(timer);
  }, []);

  return (
    <>
      <Navbar title="ResolveOps" updatedAt={updatedAt} />

      <main className="dashboard">
        {errorMessage && <p className="dashboard-message dashboard-error">{errorMessage}</p>}

        {!errorMessage && overview === null && <p className="dashboard-message">Loading dashboard...</p>}

        {overview !== null && (
          <>
            <section className="kpi-row">
              <StatCard
                label="AI deflection rate"
                value={`${overview.kpis.deflection_rate}%`}
                hint="of tickets fixed by the AI suggestion"
                highlight
              />
              <StatCard label="Total tickets" value={overview.kpis.total} hint="raised in Slack" />
              <StatCard label="Open" value={overview.kpis.open} hint="waiting for a fix" />
              <StatCard label="Resolved by AI" value={overview.kpis.solved_by_ai} hint="no admin needed" />
              <StatCard label="Needs review" value={overview.kpis.needs_review} hint="flagged by the AI guard" />
            </section>

            <section className="chart-row">
              <BarChartCard
                title="Tickets by category"
                subtitle="How the AI classified each issue"
                data={toCategoryBars(overview.by_category)}
              />
              <BarChartCard
                title="Tickets by priority"
                subtitle="P1 is the most urgent"
                data={toPriorityBars(overview.by_priority)}
              />
            </section>

            <section className="list-row">
              <TicketList
                title="Recent tickets"
                subtitle="The last 10 tickets raised"
                tickets={overview.recent}
                emptyMessage="No tickets yet."
              />
              <TicketList
                title="Caught by the AI guard"
                subtitle="Spam, prompt injection and unclear tickets"
                tickets={overview.flagged}
                emptyMessage="Nothing flagged. All clear."
                showFlag
              />
            </section>
          </>
        )}
      </main>
    </>
  );
}

export default App;
