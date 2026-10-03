// @spec docs/BACKLOG.md#RG-013 | docs/BACKLOG.md#RG-012 | docs/DESIGN_SYSTEM.md#6.17 | docs/DESIGN_SYSTEM_APP.md#architecture
// Accueil : surface autonome avec l'état du moteur et la connexion par jeton (DS §6.17).
import { LogIn, ShieldCheck } from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../auth";
import { Footer } from "../components/AppShell";
import { Alert } from "../components/ui/Alert";
import { Badge } from "../components/ui/Badge";
import { t, tOr } from "../i18n";
import { api, ApiError, type Health } from "../lib/api";

export function Home() {
  const { status, login } = useAuth();
  const [health, setHealth] = useState<Health | null | "error">(null);
  const [token, setToken] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .health()
      .then(setHealth)
      .catch(() => setHealth("error"));
  }, []);

  if (status === "authenticated") return <Navigate to="/journal" replace />;

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!token.trim()) {
      setError(t("home.login.required"));
      return;
    }
    setPending(true);
    setError(null);
    try {
      await login(token.trim());
    } catch (exc) {
      setError(exc instanceof ApiError && exc.status === 401 ? t("home.login.error") : t("common.error"));
    } finally {
      setPending(false);
    }
  };

  return (
    <div className="auth-page">
      <main className="card auth-card">
        <div className="brand">
          <span className="brand-mark">
            <ShieldCheck size={22} aria-hidden="true" />
          </span>
          <span>{t("app.name")}</span>
        </div>
        <h1>{t("home.title")}</h1>
        <p className="muted">{t("home.intro")}</p>

        <section aria-labelledby="engine-title" className="card">
          <h2 id="engine-title">{t("home.engine")}</h2>
          {health === null ? (
            <p className="muted">{t("home.engine.checking")}</p>
          ) : health === "error" ? (
            <dl className="pairs">
              <dt>{t("home.engine")}</dt>
              <dd>
                <Badge tone="danger">{t("home.engine.offline")}</Badge>
              </dd>
            </dl>
          ) : (
            <dl className="pairs">
              <dt>{t("home.engine")}</dt>
              <dd>
                <Badge tone="success">{t("home.engine.online")}</Badge>
              </dd>
              <dt>{t("home.engine.profile")}</dt>
              <dd>{tOr(`profile.${health.profile}`, "profile.equilibre")}</dd>
              <dt>{t("home.engine.version")}</dt>
              <dd className="mono">{health.version}</dd>
              {health.degraded.length > 0 ? (
                <>
                  <dt>{t("home.engine.degraded")}</dt>
                  <dd>{health.degraded.join(", ")}</dd>
                </>
              ) : null}
            </dl>
          )}
        </section>

        <form onSubmit={submit} className="field" noValidate>
          <label htmlFor="token">{t("home.token")}</label>
          <input
            id="token"
            className="input mono"
            type="password"
            autoComplete="current-password"
            value={token}
            onChange={(event) => setToken(event.target.value)}
            aria-describedby={error ? "token-help token-error" : "token-help"}
            aria-invalid={error ? true : undefined}
          />
          <p id="token-help" className="help">
            {t("home.token.help")}
          </p>
          {error ? (
            <Alert kind="danger" id="token-error">
              {error}
            </Alert>
          ) : null}
          <button type="submit" className="btn btn-primary" disabled={pending}>
            <LogIn size={18} aria-hidden="true" />
            {pending ? t("home.login.pending") : t("home.login")}
          </button>
        </form>
      </main>
      <Footer />
    </div>
  );
}
