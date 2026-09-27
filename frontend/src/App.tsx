import { Navigate, Route, Routes } from "react-router-dom";

import AuthGuard from "./components/AuthGuard";
import MainLayout from "./layouts/MainLayout";

import AuditTrail from "./pages/AuditTrail";
import Dashboard from "./pages/Dashboard";
import DocumentDetails from "./pages/DocumentDetails";
import Documents from "./pages/Documents";
import Login from "./pages/login";
import ReviewQueue from "./pages/ReviewQueue";
import Settings from "./pages/Settings";

export default function App() {
  return (
    <Routes>
      {/* Public */}
      <Route path="/login" element={<Login />} />

      {/* Protected application */}
      <Route element={<AuthGuard />}>
        <Route element={<MainLayout />}>
          <Route
            path="/"
            element={
              <Navigate
                to="/dashboard"
                replace
              />
            }
          />

          <Route
            path="/dashboard"
            element={<Dashboard />}
          />

          <Route
            path="/documents"
            element={<Documents />}
          />

          {/* IMPORTANT:
              This must be a dynamic route.
          */}
          <Route
            path="/documents/:documentId"
            element={<DocumentDetails />}
          />

          <Route
            path="/review"
            element={<ReviewQueue />}
          />

          <Route
            path="/audit"
            element={<AuditTrail />}
          />

          <Route
            path="/settings"
            element={<Settings />}
          />

          {/* Unknown protected routes */}
          <Route
            path="*"
            element={
              <Navigate
                to="/dashboard"
                replace
              />
            }
          />
        </Route>
      </Route>

      {/* Unknown public routes */}
      <Route
        path="*"
        element={
          <Navigate
            to="/dashboard"
            replace
          />
        }
      />
    </Routes>
  );
}