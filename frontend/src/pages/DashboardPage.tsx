import { useAuth } from "../api/auth";
import TeenDashboard from "./dashboard/TeenDashboard";
import KidDashboard from "./dashboard/KidDashboard";
import ToddlerDashboard from "./dashboard/ToddlerDashboard";
import { PageLoader } from "../components/ui";
import { Navigate } from "react-router-dom";

/** Kid home — renders the dashboard for the kid's age mode. */
export default function DashboardPage() {
  const { user, account, refresh } = useAuth();
  if (!user) return null;

  // Admins don't have their own bank account — send them to the family overview.
  if (user.role === "admin") return <Navigate to="/overview" replace />;

  if (!account) {
    return (
      <div className="card mt-8 text-center font-bold">
        No bank account yet — ask a parent to set one up 🐷
      </div>
    );
  }

  const props = { account, onChanged: refresh };
  switch (user.ui_mode) {
    case "toddler":
      return <ToddlerDashboard account={account} />;
    case "kid":
      return <KidDashboard {...props} />;
    default:
      return <TeenDashboard {...props} />;
  }
}

export { PageLoader };
