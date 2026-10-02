// @spec docs/BACKLOG.md#RG-013 | docs/DESIGN_SYSTEM.md#5.4 | docs/DESIGN_SYSTEM_APP.md#architecture | docs/DESIGN_SYSTEM_APP.md#responsive
// Coquille de l'application : barre latérale de premier degré, en-tête de destination, pied de page.
import { FlaskConical, Gauge, LogOut, ScrollText, ShieldCheck, SlidersHorizontal } from "lucide-react";
import type { ReactNode } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../auth";
import { t, type MessageKey } from "../i18n";

const DESTINATIONS: { to: string; key: MessageKey; icon: typeof ScrollText }[] = [
  { to: "/journal", key: "nav.journal", icon: ScrollText },
  { to: "/bac-a-sable", key: "nav.sandbox", icon: FlaskConical },
  { to: "/politiques", key: "nav.policies", icon: SlidersHorizontal },
  { to: "/moteurs", key: "nav.engines", icon: Gauge },
];

export function Footer() {
  return (
    <footer className="footer">
      <span>{t("footer.by")}</span>
      <a href={t("footer.link")} rel="noreferrer" target="_blank">
        {t("footer.link")}
      </a>
    </footer>
  );
}

export function AppShell({ title, actions, children }: { title: string; actions?: ReactNode; children: ReactNode }) {
  const { logout } = useAuth();
  const navigate = useNavigate();
  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">
            <ShieldCheck size={22} aria-hidden="true" />
          </span>
          <span>{t("app.name")}</span>
        </div>
        <nav aria-label={t("nav.label")}>
          <ul className="nav-list">
            {DESTINATIONS.map(({ to, key, icon: Icon }) => (
              <li key={to}>
                <NavLink to={to} className="nav-link">
                  <Icon size={20} aria-hidden="true" />
                  <span>{t(key)}</span>
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>
      </aside>
      <div className="main">
        <header className="topbar">
          <h1>{title}</h1>
          <div className="btn-group">
            {actions}
            <button
              type="button"
              className="btn"
              onClick={async () => {
                await logout();
                navigate("/");
              }}
            >
              <LogOut size={18} aria-hidden="true" />
              {t("nav.logout")}
            </button>
          </div>
        </header>
        <main className="content">{children}</main>
        <Footer />
      </div>
    </div>
  );
}
