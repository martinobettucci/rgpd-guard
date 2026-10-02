// @spec docs/BACKLOG.md#RG-013 | docs/BACKLOG.md#RG-011 | docs/DESIGN_SYSTEM.md#6.14 | docs/DESIGN_SYSTEM.md#8.2 | docs/DESIGN_SYSTEM_APP.md#visualisation | docs/DESIGN_SYSTEM_APP.md#responsive
// Journal : synthèse, filtres et tableau paginé des événements (aucune valeur brute, aperçus masqués).
import { ChevronLeft, ChevronRight, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useAuth } from "../auth";
import { AppShell } from "../components/AppShell";
import { DecisionBadge } from "../components/DecisionBadge";
import { Alert } from "../components/ui/Alert";
import { Skeleton } from "../components/ui/Skeleton";
import { t, tOr } from "../i18n";
import { api, ApiError, type AuditPage, type AuditStats } from "../lib/api";
import { formatDate, formatMs } from "../lib/format";

const PAGE_SIZE = 20;
const DECISIONS = ["block", "warn", "pseudonymize", "allow", "deny", "rehydrate", "leak"];
const EVENTS = ["user_prompt_submit", "pre_tool_use", "post_tool_use", "post_tool_use_failure", "post_tool_batch"];

export function Journal() {
  const { expire } = useAuth();
  const [stats, setStats] = useState<AuditStats | null>(null);
  const [labels, setLabels] = useState<Record<string, string>>({});
  const [page, setPage] = useState<AuditPage | null>(null);
  const [error, setError] = useState(false);
  const [offset, setOffset] = useState(0);
  const [filters, setFilters] = useState({ decision: "", event: "", label: "" });

  const load = useCallback(async () => {
    setError(false);
    try {
      const [statsData, pageData, policy] = await Promise.all([
        api.stats(),
        api.events({ limit: PAGE_SIZE, offset, ...filters }),
        api.policy(),
      ]);
      setStats(statsData);
      setPage(pageData);
      setLabels(policy.labels);
    } catch (exc) {
      if (exc instanceof ApiError && exc.status === 401) expire();
      else setError(true);
    }
  }, [offset, filters, expire]);

  useEffect(() => {
    void load();
  }, [load]);

  const setFilter = (name: keyof typeof filters, value: string) => {
    setOffset(0);
    setFilters((current) => ({ ...current, [name]: value }));
  };

  const pages = page ? Math.max(1, Math.ceil(page.total / PAGE_SIZE)) : 1;
  const current = Math.floor(offset / PAGE_SIZE) + 1;
  const labelName = (code: string) => labels[code] ?? code;

  return (
    <AppShell
      title={t("journal.title")}
      actions={
        <button type="button" className="btn" onClick={() => void load()}>
          <RefreshCw size={18} aria-hidden="true" />
          {t("common.refresh")}
        </button>
      }
    >
      {error ? <Alert kind="danger">{t("common.error")}</Alert> : null}

      <section className="card" aria-labelledby="stats-title">
        <h2 id="stats-title">{t("journal.stats")}</h2>
        {stats === null ? (
          <Skeleton lines={2} />
        ) : (
          <>
            <div className="stats">
              {(
                [
                  ["journal.stats.total", stats.total],
                  ["journal.stats.block", stats.by_decision.block ?? 0],
                  ["journal.stats.pseudonymize", stats.by_decision.pseudonymize ?? 0],
                  ["journal.stats.leak", stats.by_decision.leak ?? 0],
                ] as const
              ).map(([key, value]) => (
                <div key={key} className="stat">
                  <div className="help">{t(key)}</div>
                  <div className="stat-value">{value}</div>
                </div>
              ))}
            </div>
            <h3>{t("journal.byLabel")}</h3>
            {Object.keys(stats.by_label).length === 0 ? (
              <p className="muted">{t("journal.byLabel.empty")}</p>
            ) : (
              <ul className="chips" aria-label={t("journal.byLabel")}>
                {Object.entries(stats.by_label).map(([label, count]) => (
                  <li key={label} className="badge badge-neutral">
                    {labelName(label)} : {count}
                  </li>
                ))}
              </ul>
            )}
          </>
        )}
      </section>

      <section className="card" aria-labelledby="events-title">
        <div className="card-header">
          <h2 id="events-title">{t("journal.events")}</h2>
        </div>
        <fieldset className="form-row" style={{ border: 0, padding: 0, margin: 0 }}>
          <legend className="sr-only">{t("journal.filters")}</legend>
          <div className="field">
            <label htmlFor="filter-decision">{t("journal.filter.decision")}</label>
            <select
              id="filter-decision"
              className="select"
              value={filters.decision}
              onChange={(event) => setFilter("decision", event.target.value)}
            >
              <option value="">{t("journal.filter.all")}</option>
              {DECISIONS.map((value) => (
                <option key={value} value={value}>
                  {tOr(`decision.${value}`, "decision.unknown")}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="filter-event">{t("journal.filter.event")}</label>
            <select
              id="filter-event"
              className="select"
              value={filters.event}
              onChange={(event) => setFilter("event", event.target.value)}
            >
              <option value="">{t("journal.filter.all")}</option>
              {EVENTS.map((value) => (
                <option key={value} value={value}>
                  {tOr(`event.${value}`, "event.unknown")}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="filter-label">{t("journal.filter.label")}</label>
            <select
              id="filter-label"
              className="select"
              value={filters.label}
              onChange={(event) => setFilter("label", event.target.value)}
            >
              <option value="">{t("journal.filter.all")}</option>
              {Object.entries(labels).map(([code, name]) => (
                <option key={code} value={code}>
                  {name}
                </option>
              ))}
            </select>
          </div>
        </fieldset>

        {page === null ? (
          <Skeleton lines={5} />
        ) : page.events.length === 0 ? (
          <p className="empty">{t("journal.empty")}</p>
        ) : (
          <div className="table-scroll">
            <table className="data">
              <thead>
                <tr>
                  <th scope="col">{t("journal.col.date")}</th>
                  <th scope="col">{t("journal.col.event")}</th>
                  <th scope="col">{t("journal.col.tool")}</th>
                  <th scope="col">{t("journal.col.decision")}</th>
                  <th scope="col">{t("journal.col.entities")}</th>
                  <th scope="col">{t("journal.col.profile")}</th>
                  <th scope="col" className="num">
                    {t("journal.col.latency")}
                  </th>
                </tr>
              </thead>
              <tbody>
                {page.events.map((item) => (
                  <tr key={item.id}>
                    <td className="mono">{formatDate(item.ts)}</td>
                    <td>
                      {tOr(`event.${item.event}`, "event.unknown")}
                      {item.subagent ? <span className="help"> ({t("journal.subagent")})</span> : null}
                    </td>
                    <td className="mono">{item.tool ?? ""}</td>
                    <td>
                      <div className="chips">
                        <DecisionBadge decision={item.decision} />
                        {item.bypass ? <span className="badge badge-accent">{t("journal.bypass")}</span> : null}
                        {item.partial ? <span className="badge badge-neutral">{t("journal.partial")}</span> : null}
                      </div>
                    </td>
                    <td>
                      {item.entities.length === 0 ? (
                        <span className="help">{t("journal.noEntity")}</span>
                      ) : (
                        <ul className="chips">
                          {item.entities.map((entity, index) => (
                            <li key={index} className="badge badge-neutral">
                              {labelName(entity.label)}
                              {entity.preview ? <span className="mono"> {entity.preview}</span> : null}
                            </li>
                          ))}
                        </ul>
                      )}
                    </td>
                    <td>{tOr(`profile.${item.profile}`, "profile.equilibre")}</td>
                    <td className="num mono">{formatMs(item.latency_ms)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <nav className="pager" aria-label={t("journal.events")}>
          <button
            type="button"
            className="btn"
            disabled={offset === 0}
            onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
          >
            <ChevronLeft size={18} aria-hidden="true" />
            {t("common.previous")}
          </button>
          <span aria-live="polite">{t("common.page", { page: current, pages })}</span>
          <button
            type="button"
            className="btn"
            disabled={current >= pages}
            onClick={() => setOffset(offset + PAGE_SIZE)}
          >
            {t("common.next")}
            <ChevronRight size={18} aria-hidden="true" />
          </button>
        </nav>
      </section>
    </AppShell>
  );
}
