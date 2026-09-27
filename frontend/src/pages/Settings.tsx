import { Settings as SettingsIcon, ShieldCheck, User } from "lucide-react";
import { getStoredUser } from "../services/api";

export default function Settings() {
  const user = getStoredUser();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-[#263746]">Settings</h1>
        <p className="mt-1 text-sm text-[#687786]">
          Manage your BhoomiAI workspace and account preferences.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <section className="rounded-xl border border-[#E4E9EE] bg-white">
          <div className="flex items-center gap-3 border-b border-[#E4E9EE] px-5 py-4">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-[#EEF3F6]">
              <User size={18} className="text-[#315A7D]" />
            </div>

            <div>
              <h2 className="text-sm font-semibold text-[#263746]">
                Account
              </h2>
              <p className="text-xs text-[#687786]">
                Current user information
              </p>
            </div>
          </div>

          <div className="space-y-4 p-5">
            <div>
              <p className="text-xs font-medium text-[#687786]">Name</p>
              <p className="mt-1 text-sm text-[#263746]">
                {user?.full_name || "—"}
              </p>
            </div>

            <div>
              <p className="text-xs font-medium text-[#687786]">Email</p>
              <p className="mt-1 text-sm text-[#263746]">
                {user?.email || "—"}
              </p>
            </div>

            <div>
              <p className="text-xs font-medium text-[#687786]">Role</p>
              <p className="mt-1 text-sm text-[#263746]">
                {user?.role || "—"}
              </p>
            </div>
          </div>
        </section>

        <section className="rounded-xl border border-[#E4E9EE] bg-white">
          <div className="flex items-center gap-3 border-b border-[#E4E9EE] px-5 py-4">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-[#EEF3F6]">
              <ShieldCheck size={18} className="text-[#5D8173]" />
            </div>

            <div>
              <h2 className="text-sm font-semibold text-[#263746]">
                Security
              </h2>
              <p className="text-xs text-[#687786]">
                Authentication and access
              </p>
            </div>
          </div>

          <div className="space-y-4 p-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-[#263746]">
                  Authentication
                </p>
                <p className="mt-1 text-xs text-[#687786]">
                  JWT-based authenticated session
                </p>
              </div>

              <span className="text-xs font-medium text-[#4F806B]">
                Active
              </span>
            </div>

            <div className="border-t border-[#E4E9EE] pt-4">
              <p className="text-sm font-medium text-[#263746]">
                Role-based access
              </p>
              <p className="mt-1 text-xs text-[#687786]">
                Access is controlled according to the authenticated user's
                assigned role.
              </p>
            </div>
          </div>
        </section>
      </div>

      <section className="rounded-xl border border-[#E4E9EE] bg-white">
        <div className="flex items-center gap-3 border-b border-[#E4E9EE] px-5 py-4">
          <SettingsIcon size={18} className="text-[#315A7D]" />
          <h2 className="text-sm font-semibold text-[#263746]">
            System Configuration
          </h2>
        </div>

        <div className="p-5">
          <p className="text-sm text-[#687786]">
            Advanced system configuration will be available to authorized
            administrators as the BhoomiAI platform is expanded.
          </p>
        </div>
      </section>
    </div>
  );
}