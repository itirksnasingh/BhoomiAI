import {
    Bell,
    ChevronDown,
    ClipboardCheck,
    FileText,
    LayoutDashboard,
    LogOut,
    Menu,
    ScrollText,
    Settings,
    X,
  } from "lucide-react";
  import { useEffect, useState } from "react";
  import {
    NavLink,
    Outlet,
    useLocation,
    useNavigate,
  } from "react-router-dom";
  import {
    getStoredUser,
    getWorkspaceNotifications,
    logout,
  } from "../services/api";
  
  const navigation = [
    {
      label: "Dashboard",
      path: "/dashboard",
      icon: LayoutDashboard,
    },
    {
      label: "Documents",
      path: "/documents",
      icon: FileText,
    },
    {
      label: "Review Queue",
      path: "/review",
      icon: ClipboardCheck,
    },
    {
      label: "Audit Trail",
      path: "/audit",
      icon: ScrollText,
    },
  ];
  
  export default function MainLayout() {
    const navigate = useNavigate();
    const location = useLocation();
  
    const user = getStoredUser();
  
    const [mobileOpen, setMobileOpen] = useState(false);
    const [notificationCount, setNotificationCount] = useState(0);
    const [userMenuOpen, setUserMenuOpen] = useState(false);
  
    useEffect(() => {
      let mounted = true;
  
      async function loadNotifications() {
        try {
          const data = await getWorkspaceNotifications();
  
          if (mounted) {
            setNotificationCount(data.unread);
          }
        } catch {
          if (mounted) {
            setNotificationCount(0);
          }
        }
      }
  
      loadNotifications();
  
      const interval = window.setInterval(
        loadNotifications,
        30_000,
      );
  
      return () => {
        mounted = false;
        window.clearInterval(interval);
      };
    }, [location.pathname]);
  
    function handleLogout() {
      logout();
      navigate("/login", { replace: true });
    }
  
    const initials =
      user?.full_name
        ?.split(" ")
        .map((part) => part[0])
        .join("")
        .slice(0, 2)
        .toUpperCase() || "U";
  
    return (
      <div className="min-h-screen bg-[#F7F9FB] text-[#263746]">
        {/* Desktop sidebar */}
        <aside className="fixed inset-y-0 left-0 z-30 hidden w-[250px] border-r border-[#E1E7EB] bg-white lg:flex lg:flex-col">
          <div className="flex h-[76px] items-center border-b border-[#EDF0F2] px-6">
            <img
              src="/bhoomiai-logo.png"
              alt="BhoomiAI"
              className="h-11 w-auto object-contain"
            />
          </div>
  
          <div className="flex-1 px-3 py-5">
            <p className="mb-3 px-3 text-[10px] font-semibold uppercase tracking-[0.14em] text-[#97A3AC]">
              Workspace
            </p>
  
            <nav className="space-y-1">
              {navigation.map((item) => {
                const Icon = item.icon;
  
                return (
                  <NavLink
                    key={item.path}
                    to={item.path}
                    className={({ isActive }) =>
                      [
                        "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition",
                        isActive
                          ? "bg-[#EEF4F6] text-[#315A7D]"
                          : "text-[#687786] hover:bg-[#F6F8F9] hover:text-[#405362]",
                      ].join(" ")
                    }
                  >
                    <Icon className="h-[17px] w-[17px]" />
  
                    <span>{item.label}</span>
  
                    {item.label === "Review Queue" &&
                      notificationCount > 0 && (
                        <span className="ml-auto rounded-full bg-[#F4EBDD] px-2 py-0.5 text-[10px] font-semibold text-[#947247]">
                          {notificationCount}
                        </span>
                      )}
                  </NavLink>
                );
              })}
            </nav>
  
            <p className="mb-3 mt-8 px-3 text-[10px] font-semibold uppercase tracking-[0.14em] text-[#97A3AC]">
              System
            </p>
  
            <NavLink
              to="/settings"
              className={({ isActive }) =>
                [
                  "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition",
                  isActive
                    ? "bg-[#EEF4F6] text-[#315A7D]"
                    : "text-[#687786] hover:bg-[#F6F8F9] hover:text-[#405362]",
                ].join(" ")
              }
            >
              <Settings className="h-[17px] w-[17px]" />
              Settings
            </NavLink>
          </div>
  
          <div className="border-t border-[#EDF0F2] p-4">
            <div className="rounded-xl bg-[#F6F8F9] p-3">
              <div className="flex items-center gap-3">
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[#E7EFF3] text-xs font-semibold text-[#315A7D]">
                  {initials}
                </div>
  
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold text-[#405362]">
                    {user?.full_name || "User"}
                  </p>
  
                  <p className="truncate text-xs text-[#8996A0]">
                    {user?.role || "User"}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </aside>
  
        {/* Mobile sidebar */}
        {mobileOpen && (
          <div className="fixed inset-0 z-50 lg:hidden">
            <button
              aria-label="Close navigation"
              onClick={() => setMobileOpen(false)}
              className="absolute inset-0 bg-[#263746]/20"
            />
  
            <aside className="relative flex h-full w-[280px] flex-col border-r border-[#E1E7EB] bg-white shadow-xl">
              <div className="flex h-[76px] items-center justify-between border-b border-[#EDF0F2] px-5">
                <img
                  src="/bhoomiai-logo.png"
                  alt="BhoomiAI"
                  className="h-10 w-auto"
                />
  
                <button
                  onClick={() => setMobileOpen(false)}
                  className="rounded-lg p-2 text-[#687786] hover:bg-[#F4F6F7]"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>
  
              <nav className="space-y-1 px-3 py-5">
                {navigation.map((item) => {
                  const Icon = item.icon;
  
                  return (
                    <NavLink
                      key={item.path}
                      to={item.path}
                      onClick={() => setMobileOpen(false)}
                      className={({ isActive }) =>
                        [
                          "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium",
                          isActive
                            ? "bg-[#EEF4F6] text-[#315A7D]"
                            : "text-[#687786]",
                        ].join(" ")
                      }
                    >
                      <Icon className="h-[17px] w-[17px]" />
                      {item.label}
                    </NavLink>
                  );
                })}
  
                <NavLink
                  to="/settings"
                  onClick={() => setMobileOpen(false)}
                  className={({ isActive }) =>
                    [
                      "mt-6 flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium",
                      isActive
                        ? "bg-[#EEF4F6] text-[#315A7D]"
                        : "text-[#687786]",
                    ].join(" ")
                  }
                >
                  <Settings className="h-[17px] w-[17px]" />
                  Settings
                </NavLink>
              </nav>
            </aside>
          </div>
        )}
  
        {/* Main area */}
        <div className="lg:pl-[250px]">
          <header className="sticky top-0 z-20 flex h-[76px] items-center justify-between border-b border-[#E1E7EB] bg-white/95 px-5 backdrop-blur-sm sm:px-7">
            <button
              onClick={() => setMobileOpen(true)}
              className="rounded-lg p-2 text-[#526575] hover:bg-[#F4F6F7] lg:hidden"
              aria-label="Open navigation"
            >
              <Menu className="h-5 w-5" />
            </button>
  
            <div className="hidden lg:block">
              <p className="text-sm font-semibold text-[#405362]">
                Land Record Intelligence
              </p>
  
              <p className="mt-0.5 text-xs text-[#8A98A2]">
                Evidence-linked validation workspace
              </p>
            </div>
  
            <div className="ml-auto flex items-center gap-2">
              <button
                className="relative rounded-lg p-2.5 text-[#687786] transition hover:bg-[#F4F6F7]"
                aria-label="Notifications"
              >
                <Bell className="h-[18px] w-[18px]" />
  
                {notificationCount > 0 && (
                  <span className="absolute right-2 top-2 h-2 w-2 rounded-full bg-[#A76565]" />
                )}
              </button>
  
              <div className="relative">
                <button
                  onClick={() =>
                    setUserMenuOpen((value) => !value)
                  }
                  className="flex items-center gap-2 rounded-lg px-2 py-1.5 transition hover:bg-[#F5F7F8]"
                >
                  <div className="flex h-8 w-8 items-center justify-center rounded-full bg-[#E7EFF3] text-[11px] font-semibold text-[#315A7D]">
                    {initials}
                  </div>
  
                  <div className="hidden text-left sm:block">
                    <p className="max-w-[150px] truncate text-xs font-semibold text-[#405362]">
                      {user?.full_name || "User"}
                    </p>
  
                    <p className="text-[10px] uppercase tracking-wide text-[#8A98A2]">
                      {user?.role || "User"}
                    </p>
                  </div>
  
                  <ChevronDown className="hidden h-4 w-4 text-[#8996A0] sm:block" />
                </button>
  
                {userMenuOpen && (
                  <div className="absolute right-0 top-12 w-52 rounded-xl border border-[#DDE5EA] bg-white p-2 shadow-[0_10px_30px_rgba(38,55,70,0.10)]">
                    <div className="border-b border-[#EDF0F2] px-3 py-2.5">
                      <p className="truncate text-sm font-semibold text-[#405362]">
                        {user?.full_name || "User"}
                      </p>
  
                      <p className="mt-0.5 truncate text-xs text-[#8996A0]">
                        {user?.email || ""}
                      </p>
                    </div>
  
                    <button
                      onClick={handleLogout}
                      className="mt-1 flex w-full items-center gap-2 rounded-lg px-3 py-2.5 text-sm text-[#687786] hover:bg-[#F7F9FA] hover:text-[#8A5555]"
                    >
                      <LogOut className="h-4 w-4" />
                      Sign out
                    </button>
                  </div>
                )}
              </div>
            </div>
          </header>
  
          <main className="min-h-[calc(100vh-76px)] bg-[#F7F9FB] p-5 sm:p-7 lg:p-8">
            <Outlet />
          </main>
        </div>
      </div>
    );
  }