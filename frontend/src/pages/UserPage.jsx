import { useEffect, useState } from "react";
import { fetchUserTickets, fetchUsers } from "../api";
import PageHeader from "../components/PageHeader";
import TicketCard from "../components/TicketCard";
import "./userpage.css";

// What an employee sees: the tickets they raised, their status and the AI suggested fix.
// Employees have no dashboard login yet, so the super admin picks which employee to view.
function UserPage({ token, onUnauthorized }) {
  const [users, setUsers] = useState(null);
  const [selectedSlackId, setSelectedSlackId] = useState("");
  const [tickets, setTickets] = useState(null);
  const [errorMessage, setErrorMessage] = useState("");

  function handleError(error) {
    if (error.message === "UNAUTHORIZED") {
      onUnauthorized();
    } else {
      setErrorMessage("Could not load the tickets. Is the backend running?");
    }
  }

  // 1. Load the list of users once, and select the first one.
  useEffect(() => {
    fetchUsers(token)
      .then((userList) => {
        setUsers(userList);
        if (userList.length > 0) {
          setSelectedSlackId(userList[0].slack_id);
        }
      })
      .catch(handleError);
  }, [token]);

  // 2. Load the selected user's tickets, again every time another user is picked.
  useEffect(() => {
    if (selectedSlackId === "") {
      return;
    }

    setTickets(null);
    fetchUserTickets(token, selectedSlackId)
      .then((ticketList) => setTickets(ticketList))
      .catch(handleError);
  }, [token, selectedSlackId]);

  return (
    <main className="dashboard">
      <PageHeader title="My tickets" subtitle="The tickets an employee raised in Slack, and what happened to them">
        {users !== null && users.length > 0 && (
          <label className="user-picker">
            Viewing as
            <select
              className="user-picker-select"
              value={selectedSlackId}
              onChange={(event) => setSelectedSlackId(event.target.value)}
            >
              {users.map((user) => (
                <option key={user.slack_id} value={user.slack_id}>
                  {user.name}
                </option>
              ))}
            </select>
          </label>
        )}
      </PageHeader>

      {errorMessage && <p className="dashboard-message dashboard-error">{errorMessage}</p>}

      {users !== null && users.length === 0 && <p className="dashboard-message">No one has raised a ticket yet.</p>}

      {!errorMessage && selectedSlackId !== "" && tickets === null && (
        <p className="dashboard-message">Loading tickets...</p>
      )}

      {tickets !== null && (
        <section className="user-ticket-list">
          {tickets.map((ticket) => (
            <TicketCard key={ticket.id} ticket={ticket} />
          ))}
        </section>
      )}
    </main>
  );
}

export default UserPage;
