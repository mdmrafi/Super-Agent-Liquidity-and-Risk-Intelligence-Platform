import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./context/AuthContext";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
const homes = {
  agent: "/cockpit",
  field_officer: "/network",
  provider_ops: "/provider",
  risk_team: "/risk",
};
function Guard() {
  const { user, loading } = useAuth();
  if (loading)
    return (
      <div className="grid min-h-screen place-items-center">
        <div className="h-9 w-9 animate-spin rounded-full border-4 border-slate-200 border-t-blue-600" />
      </div>
    );
  return user ? <Dashboard /> : <Navigate to="/login" replace />;
}
export default function App() {
  const { user } = useAuth();
  return (
    <Routes>
      <Route
        path="/login"
        element={
          user ? (
            <Navigate to={homes[user.role] || "/assistant"} replace />
          ) : (
            <Login />
          )
        }
      />
      <Route path="/*" element={<Guard />} />
    </Routes>
  );
}
