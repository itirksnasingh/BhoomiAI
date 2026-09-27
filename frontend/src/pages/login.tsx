import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import {
  AlertCircle,
  ArrowRight,
  CheckCircle2,
  Eye,
  EyeOff,
  FileCheck2,
  LoaderCircle,
  LockKeyhole,
  ShieldCheck,
} from "lucide-react";
import { useLocation, useNavigate } from "react-router-dom";
import { checkBackendHealth, getToken, login } from "../services/api";

export default function Login() {
  const navigate = useNavigate();
  const location = useLocation();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const [error, setError] = useState("");
  const [backendOnline, setBackendOnline] = useState<boolean | null>(null);

  useEffect(() => {
    if (getToken()) {
      navigate("/dashboard", { replace: true });
      return;
    }

    checkBackendHealth().then(setBackendOnline);
  }, [navigate]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    setError("");

    const normalizedEmail = email.trim().toLowerCase();

    if (!normalizedEmail) {
      setError("Please enter your email address.");
      return;
    }

    if (!password) {
      setError("Please enter your password.");
      return;
    }

    setIsSubmitting(true);

    try {
      await login(normalizedEmail, password);

      const from =
        typeof location.state?.from === "string"
          ? location.state.from
          : "/dashboard";

      navigate(from, { replace: true });
    } catch (err) {
      const message =
        err instanceof Error
          ? err.message
          : "Unable to sign in. Please try again.";

      setError(message);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen bg-[#F7F9FB]">
      <header className="border-b border-[#E1E7EB] bg-white">
        <div className="mx-auto flex h-[72px] max-w-[1400px] items-center justify-between px-6 lg:px-10">
          <div className="flex items-center">
            <img
              src="/bhoomiai-logo.png"
              alt="BhoomiAI — Trusted Land Records. Smarter Decisions."
              className="h-12 w-auto object-contain"
            />
          </div>

          <div className="hidden items-center gap-2 text-sm text-[#687786] sm:flex">
            <ShieldCheck className="h-4 w-4 text-[#5D8173]" />
            Secure workspace
          </div>
        </div>
      </header>

      <main className="mx-auto flex min-h-[calc(100vh-72px)] max-w-[1400px] items-center px-6 py-12 lg:px-10">
        <div className="grid w-full gap-16 lg:grid-cols-[1.1fr_0.9fr] lg:items-center">
          {/* Left side */}
          <section className="hidden lg:block">
            <div className="max-w-2xl">
              <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-[#DCE8E3] bg-[#F3F8F5] px-3.5 py-2 text-xs font-semibold text-[#5D8173]">
                <FileCheck2 className="h-4 w-4" />
                READ → VERIFY → TRUST
              </div>

              <h1 className="text-5xl font-semibold leading-[1.08] tracking-[-0.03em] text-[#263746]">
                Intelligent land records,
                <span className="block text-[#315A7D]">
                  built for trusted decisions.
                </span>
              </h1>

              <p className="mt-6 max-w-xl text-base leading-7 text-[#687786]">
                BhoomiAI transforms scanned land records into structured,
                evidence-linked information and identifies records that need
                verification.
              </p>

              <div className="mt-10 grid max-w-xl grid-cols-3 gap-3">
                <InfoItem
                  icon={<FileCheck2 className="h-4 w-4" />}
                  title="Extract"
                  text="Structured fields"
                />

                <InfoItem
                  icon={<ShieldCheck className="h-4 w-4" />}
                  title="Validate"
                  text="Evidence & rules"
                />

                <InfoItem
                  icon={<CheckCircle2 className="h-4 w-4" />}
                  title="Verify"
                  text="Human review"
                />
              </div>
            </div>
          </section>

          {/* Login card */}
          <section className="mx-auto w-full max-w-[460px]">
            <div className="rounded-2xl border border-[#DDE5EA] bg-white p-7 shadow-[0_12px_40px_rgba(38,55,70,0.07)] sm:p-9">
              <div className="mb-8">
                <div className="mb-5 flex h-11 w-11 items-center justify-center rounded-xl bg-[#EEF4F6]">
                  <LockKeyhole className="h-5 w-5 text-[#315A7D]" />
                </div>

                <h2 className="text-2xl font-semibold tracking-tight text-[#263746]">
                  Sign in
                </h2>

                <p className="mt-2 text-sm leading-6 text-[#748390]">
                  Access your BhoomiAI land record workspace.
                </p>
              </div>

              {backendOnline === false && (
                <div className="mb-5 flex gap-3 rounded-xl border border-[#E7D9C8] bg-[#FBF6EF] p-3.5 text-sm text-[#806A4D]">
                  <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />

                  <div>
                    <p className="font-semibold">
                      Backend connection unavailable
                    </p>

                    <p className="mt-1 leading-5">
                      Make sure the BhoomiAI FastAPI server is running on
                      localhost:8000.
                    </p>
                  </div>
                </div>
              )}

              {backendOnline === true && (
                <div className="mb-5 flex items-center gap-2 text-xs font-medium text-[#5D8173]">
                  <span className="h-2 w-2 rounded-full bg-[#6D9585]" />
                  BhoomiAI backend connected
                </div>
              )}

              {error && (
                <div
                  role="alert"
                  className="mb-5 flex gap-3 rounded-xl border border-[#E8D6D6] bg-[#FBF3F3] p-3.5 text-sm text-[#8A5555]"
                >
                  <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />

                  <span>{error}</span>
                </div>
              )}

              <form onSubmit={handleSubmit} className="space-y-5">
                <div>
                  <label
                    htmlFor="email"
                    className="mb-2 block text-sm font-semibold text-[#405362]"
                  >
                    Email address
                  </label>

                  <input
                    id="email"
                    name="email"
                    type="email"
                    autoComplete="email"
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    placeholder="Enter your email"
                    disabled={isSubmitting}
                    className="h-12 w-full rounded-lg border border-[#D7E0E5] bg-white px-3.5 text-sm text-[#263746] shadow-sm outline-none transition placeholder:text-[#9AA8B3] focus:border-[#7193A7] focus:ring-4 focus:ring-[#EAF1F4] disabled:bg-[#F4F6F7]"
                  />
                </div>

                <div>
                  <label
                    htmlFor="password"
                    className="mb-2 block text-sm font-semibold text-[#405362]"
                  >
                    Password
                  </label>

                  <div className="relative">
                    <input
                      id="password"
                      name="password"
                      type={showPassword ? "text" : "password"}
                      autoComplete="current-password"
                      value={password}
                      onChange={(event) => setPassword(event.target.value)}
                      placeholder="Enter your password"
                      disabled={isSubmitting}
                      className="h-12 w-full rounded-lg border border-[#D7E0E5] bg-white px-3.5 pr-12 text-sm text-[#263746] shadow-sm outline-none transition placeholder:text-[#9AA8B3] focus:border-[#7193A7] focus:ring-4 focus:ring-[#EAF1F4] disabled:bg-[#F4F6F7]"
                    />

                    <button
                      type="button"
                      onClick={() => setShowPassword((value) => !value)}
                      disabled={isSubmitting}
                      aria-label={
                        showPassword ? "Hide password" : "Show password"
                      }
                      className="absolute right-3 top-1/2 -translate-y-1/2 rounded-md p-1.5 text-[#81909B] transition hover:bg-[#F3F6F8] hover:text-[#526575]"
                    >
                      {showPassword ? (
                        <EyeOff className="h-4 w-4" />
                      ) : (
                        <Eye className="h-4 w-4" />
                      )}
                    </button>
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="flex h-12 w-full items-center justify-center gap-2 rounded-lg bg-[#315A7D] px-4 text-sm font-semibold text-white shadow-sm transition hover:bg-[#294D6B] disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {isSubmitting ? (
                    <>
                      <LoaderCircle className="h-4 w-4 animate-spin" />
                      Signing in...
                    </>
                  ) : (
                    <>
                      Sign in
                      <ArrowRight className="h-4 w-4" />
                    </>
                  )}
                </button>
              </form>

              <div className="mt-7 border-t border-[#EDF0F2] pt-5">
                <div className="flex items-start gap-2.5 text-xs leading-5 text-[#87949E]">
                  <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-[#6D9585]" />

                  <p>
                    Your session is authenticated through the BhoomiAI
                    backend. Access is controlled by your assigned role.
                  </p>
                </div>
              </div>
            </div>

            <p className="mt-5 text-center text-xs text-[#98A4AC]">
              BhoomiAI · Evidence-linked land record intelligence
            </p>
          </section>
        </div>
      </main>
    </div>
  );
}

interface InfoItemProps {
  icon: React.ReactNode;
  title: string;
  text: string;
}

function InfoItem({ icon, title, text }: InfoItemProps) {
  return (
    <div className="rounded-xl border border-[#E0E7EB] bg-white p-4">
      <div className="mb-3 flex h-8 w-8 items-center justify-center rounded-lg bg-[#EEF4F6] text-[#5D8173]">
        {icon}
      </div>

      <p className="text-xs font-semibold text-[#405362]">{title}</p>

      <p className="mt-1 text-xs text-[#87949E]">{text}</p>
    </div>
  );
}