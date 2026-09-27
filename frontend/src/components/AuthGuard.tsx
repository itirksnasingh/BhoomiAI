import {
  Navigate,
  Outlet,
  useLocation,
} from "react-router-dom";

import {
  getToken,
  isAuthenticated,
} from "../services/api";

export default function AuthGuard() {
  const location = useLocation();

  const token = getToken();

  if (!token || !isAuthenticated()) {
    return (
      <Navigate
        to="/login"
        replace
        state={{
          from: location.pathname,
        }}
      />
    );
  }

  return <Outlet />;
}