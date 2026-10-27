import { zodResolver } from "@hookform/resolvers/zod";
import { Droplet } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Alert } from "@/components/ui/states";
import { ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";

const schema = z.object({
  email: z.string().trim().min(1, "Email is required").email("Enter a valid email address"),
  password: z.string().min(1, "Password is required"),
});
type FormValues = z.infer<typeof schema>;

export function LoginPage() {
  const { session, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [error, setError] = useState<string | null>(null);
  const from = (location.state as { from?: string } | null)?.from ?? "/";

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  if (session) return <Navigate to={from} replace />;

  const onSubmit = handleSubmit(async (values) => {
    setError(null);
    try {
      await login(values.email, values.password);
      navigate(from, { replace: true });
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Unable to sign in. Check that the API server is running.");
    }
  });

  return (
    <div className="flex min-h-screen flex-col lg:flex-row">
      <div className="flex flex-col justify-between bg-nav px-8 py-8 text-nav-fg lg:w-[44%] lg:px-12 lg:py-12">
        <div className="flex items-center gap-2">
          <span className="flex size-8 items-center justify-center rounded bg-blood">
            <Droplet className="size-5 fill-white text-white" aria-hidden />
          </span>
          <span className="text-lg font-semibold text-white">BloodBridge</span>
        </div>
        <div className="my-10 hidden max-w-md lg:block">
          <h1 className="text-3xl font-semibold leading-tight text-white">Blood bank operations, coordinated.</h1>
          <p className="mt-4 text-nav-muted">
            Inventory, urgent requests, consenting donors and city-level availability in one place, for blood banks, hospitals
            and authorised coordinators.
          </p>
        </div>
        <p className="hidden text-xs text-nav-muted lg:block">
          Clinical compatibility, screening and crossmatching remain the responsibility of qualified blood-bank personnel.
        </p>
      </div>

      <div className="flex flex-1 items-center justify-center px-4 py-10">
        <div className="w-full max-w-sm">
          <h2 className="text-xl font-semibold text-ink">Staff sign in</h2>
          <p className="mt-1 text-sm text-ink-muted">For administrators, blood bank managers and donor coordinators.</p>

          <form onSubmit={onSubmit} className="mt-6 space-y-4" noValidate>
            {error && <Alert tone="danger">{error}</Alert>}
            <div>
              <label htmlFor="email" className="field-label">
                Email
              </label>
              <input id="email" type="email" autoComplete="username" className="input" aria-invalid={!!errors.email} {...register("email")} />
              {errors.email && <p className="mt-1 text-xs text-danger">{errors.email.message}</p>}
            </div>
            <div>
              <label htmlFor="password" className="field-label">
                Password
              </label>
              <input
                id="password"
                type="password"
                autoComplete="current-password"
                className="input"
                aria-invalid={!!errors.password}
                {...register("password")}
              />
              {errors.password && <p className="mt-1 text-xs text-danger">{errors.password.message}</p>}
            </div>
            <Button type="submit" className="w-full" loading={isSubmitting}>
              Sign in
            </Button>
          </form>

          <div className="mt-8 rounded border border-border bg-surface p-4">
            <p className="text-sm font-medium text-ink">Need blood urgently?</p>
            <p className="mt-1 text-sm text-ink-muted">
              Contact the hospital treating the patient or call emergency services (1122) first. You can also{" "}
              <Link to="/public" className="font-medium text-primary hover:underline">
                submit a request or check public availability
              </Link>
              .
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
