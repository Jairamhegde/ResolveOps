import { fetchAdmins } from "../api";
import { useApi } from "../useApi";
import { CATEGORIES, categoryLabel, roleLabel } from "../format";
import PageHeader from "../components/PageHeader";
import { Metric, MetricStrip } from "../components/Metrics";
import { ErrorMessage, Loading, Section } from "../components/Section";
import "./adminspage.css";

// Who the admins are, which field each looks after, and how much open work is in that field. Super admins only.
function AdminsPage({ token }) {
  const admins = useApi(() => fetchAdmins(token), [token]);

  return (
    <div className="page">
      <PageHeader title="Admins" subtitle="Everyone who can resolve tickets, and the field they look after" />

      {admins.error && <ErrorMessage message={admins.error} onRetry={admins.reload} />}
      {!admins.data && !admins.error && <Loading />}
      {admins.data && <AdminList admins={admins.data} />}
    </div>
  );
}

function AdminList({ admins }) {
  const coveredCategories = admins.map((admin) => admin.category);
  const uncovered = CATEGORIES.filter((category) => !coveredCategories.includes(category.value));
  const superAdmins = admins.filter((admin) => admin.role === "super_admin").length;

  return (
    <>
      <MetricStrip label="Admin coverage">
        <Metric label="Admins" value={admins.length} detail={`${superAdmins} super ${superAdmins === 1 ? "admin" : "admins"}`} />
        <Metric
          label="Fields covered"
          value={`${CATEGORIES.length - uncovered.length} of ${CATEGORIES.length}`}
          detail={uncovered.length ? `No admin for ${uncovered.map((category) => category.label).join(", ")}` : "Every field has an admin"}
        />
        <Metric
          label="Dashboard access"
          value={admins.filter((admin) => admin.can_sign_in).length}
          detail="admins with a dashboard password"
        />
      </MetricStrip>

      <Section title="All admins" subtitle="Open work is counted for each admin's field" flush>
        <div className="table-scroll">
          <table className="ticket-table admin-table">
            <thead>
              <tr>
                <th scope="col">Admin</th>
                <th scope="col">Field</th>
                <th scope="col">Signs in with</th>
                <th scope="col" className="cell-number">Open in field</th>
                <th scope="col" className="cell-number">High severity open</th>
                <th scope="col" className="cell-number">Closed in field</th>
              </tr>
            </thead>
            <tbody>
              {admins.map((admin) => (
                <tr key={admin.id}>
                  <td>
                    <p className="admin-name">{admin.name || admin.email}</p>
                    {admin.name && <p className="admin-email">{admin.email}</p>}
                  </td>
                  <td>
                    {roleLabel(admin.role)}
                    {admin.category && <p className="admin-email">{categoryLabel(admin.category)} tickets</p>}
                    {admin.role === "super_admin" && <p className="admin-email">Every category</p>}
                  </td>
                  <td className="cell-muted">{admin.can_sign_in ? "Slack and dashboard" : "Slack only"}</td>
                  <td className="cell-number">{admin.open_tickets ?? "–"}</td>
                  <td className={admin.high_severity_open > 0 ? "cell-number cell-alert" : "cell-number"}>
                    {admin.high_severity_open ?? "–"}
                  </td>
                  <td className="cell-number">{admin.resolved ?? "–"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>
    </>
  );
}

export default AdminsPage;
