// @spec docs/BACKLOG.md#RG-016 | docs/BACKLOG.md#RG-017 | docs/DESIGN_SYSTEM.md#6.13 | docs/DESIGN_SYSTEM.md#6.14 | docs/DESIGN_SYSTEM.md#14.6 | docs/DESIGN_SYSTEM_APP.md#architecture | docs/DESIGN_SYSTEM_APP.md#visualisation
// Moteurs : état et temps de chargement des composants, profils, coffre, dernier banc d'évaluation.
import { CircleCheck, CircleX } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useAuth } from "../auth";
import { AppShell } from "../components/AppShell";
import { Alert } from "../components/ui/Alert";
import { Badge } from "../components/ui/Badge";
import { Skeleton } from "../components/ui/Skeleton";
import { t, tOr } from "../i18n";
import { api, ApiError, type EnginesResponse, type Scores } from "../lib/api";
import { formatDate, formatMs, formatScore } from "../lib/format";

function ScoresTable({ rows, names, heading }: { rows: [string, Scores][]; names: Record<string, string>; heading: string }) {
  return (
    <div className="table-scroll">
      <table className="data">
        <thead>
          <tr>
            <th scope="col">{heading}</th>
            <th scope="col" className="num">
              {t("engines.col.precision")}
            </th>
            <th scope="col" className="num">
              {t("engines.col.recall")}
            </th>
            <th scope="col" className="num">
              {t("engines.col.f1")}
            </th>
            <th scope="col" className="num">
              {t("engines.col.counts")}
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map(([code, scores]) => (
            <tr key={code}>
              <td>{names[code] ?? code}</td>
              <td className="num mono">{formatScore(scores.precision)}</td>
              <td className="num mono">{formatScore(scores.recall)}</td>
              <td className="num mono">{formatScore(scores.f1)}</td>
              <td className="num mono">
                {scores.tp} / {scores.fp} / {scores.fn}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function Engines() {
  const { expire } = useAuth();
  const [data, setData] = useState<EnginesResponse | null>(null);
  const [error, setError] = useState(false);
  const [detail, setDetail] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setData(await api.engines());
    } catch (exc) {
      if (exc instanceof ApiError && exc.status === 401) expire();
      else setError(true);
    }
  }, [expire]);

  useEffect(() => {
    void load();
  }, [load]);

  const results = data?.bench?.results ?? [];
  const selected =
    results.find((result) => result.profile === (detail ?? data?.default_profile)) ?? results[0] ?? null;

  return (
    <AppShell title={t("engines.title")}>
      {error ? <Alert kind="danger">{t("common.error")}</Alert> : null}
      {data === null ? (
        <section className="card">
          <Skeleton lines={5} />
        </section>
      ) : (
        <>
          <div className="grid-2">
            <section className="card" aria-labelledby="components-title">
              <h2 id="components-title">{t("engines.components")}</h2>
              <ul className="list-rows">
                {data.components.map((component) => (
                  <li key={component.name}>
                    <div>
                      <div className="mono">{component.name}</div>
                      {Object.keys(component.detail).length > 0 ? (
                        <div className="help">{Object.values(component.detail).join(" · ")}</div>
                      ) : null}
                      {component.ready ? (
                        <div className="help">{t("engines.loadTime", { ms: formatMs(component.load_ms) })}</div>
                      ) : null}
                      {component.error ? <div className="help mono">{component.error}</div> : null}
                    </div>
                    {component.ready ? (
                      <Badge tone="success" icon={CircleCheck}>
                        {t("engines.ready")}
                      </Badge>
                    ) : (
                      <Badge tone="danger" icon={CircleX}>
                        {t("engines.unavailable")}
                      </Badge>
                    )}
                  </li>
                ))}
              </ul>
            </section>
            <section className="card" aria-labelledby="profiles-title">
              <h2 id="profiles-title">{t("engines.profiles")}</h2>
              <ul className="list-rows">
                {Object.entries(data.profiles).map(([name, profile]) => (
                  <li key={name}>
                    <div>
                      <div>
                        {tOr(`profile.${name}`, "profile.equilibre")}
                        {name === data.default_profile ? (
                          <span className="help"> ({t("engines.profile.default")})</span>
                        ) : null}
                      </div>
                      <div className="help mono">{profile.detectors.join(", ")}</div>
                      {profile.classifiers_prompt.length > 0 ? (
                        <div className="help">
                          {t(
                            profile.classifiers_output.length > 0
                              ? "engines.profile.classifiers.all"
                              : "engines.profile.classifiers.prompt",
                            { names: profile.classifiers_prompt.join(", ") },
                          )}
                        </div>
                      ) : null}
                    </div>
                    {profile.missing.length === 0 ? (
                      <Badge tone="success" icon={CircleCheck}>
                        {t("engines.profile.complete")}
                      </Badge>
                    ) : (
                      <Badge tone="accent">{t("engines.profile.missing", { names: profile.missing.join(", ") })}</Badge>
                    )}
                  </li>
                ))}
              </ul>
              <h3>{t("engines.vault")}</h3>
              <dl className="pairs">
                <dt>{t("engines.vault.sessions")}</dt>
                <dd className="mono">{data.vault.sessions}</dd>
                <dt>{t("engines.vault.tokens")}</dt>
                <dd className="mono">{data.vault.tokens}</dd>
              </dl>
            </section>
          </div>

          <section className="card" aria-labelledby="bench-title">
            <h2 id="bench-title">{t("engines.bench")}</h2>
            {data.bench === null ? (
              <p className="muted">{t("engines.bench.none")}</p>
            ) : (
              <>
                <p className="help">
                  {t("engines.bench.generated", {
                    date: formatDate(data.bench.generated_at),
                    records: data.bench.corpus.records,
                  })}
                </p>
                <div className="table-scroll">
                  <table className="data">
                    <thead>
                      <tr>
                        <th scope="col">{t("engines.col.profile")}</th>
                        <th scope="col" className="num">
                          {t("engines.col.precision")}
                        </th>
                        <th scope="col" className="num">
                          {t("engines.col.recall")}
                        </th>
                        <th scope="col" className="num">
                          {t("engines.col.f1")}
                        </th>
                        <th scope="col" className="num">
                          {t("engines.col.p50")}
                        </th>
                        <th scope="col" className="num">
                          {t("engines.col.p95")}
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.bench.results.map((result) => (
                        <tr key={result.profile}>
                          <td>{tOr(`profile.${result.profile}`, "profile.equilibre")}</td>
                          <td className="num mono">{formatScore(result.global.precision)}</td>
                          <td className="num mono">{formatScore(result.global.recall)}</td>
                          <td className="num mono">{formatScore(result.global.f1)}</td>
                          <td className="num mono">{formatMs(result.latency_ms.p50)}</td>
                          <td className="num mono">{formatMs(result.latency_ms.p95)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {selected ? (
                  <>
                    <div className="form-row">
                      <div className="field">
                        <label htmlFor="bench-profile">{t("engines.bench.detail")}</label>
                        <select
                          id="bench-profile"
                          className="select"
                          value={selected.profile}
                          onChange={(event) => setDetail(event.target.value)}
                        >
                          {data.bench.results.map((result) => (
                            <option key={result.profile} value={result.profile}>
                              {tOr(`profile.${result.profile}`, "profile.equilibre")}
                            </option>
                          ))}
                        </select>
                      </div>
                    </div>
                    <h3>{t("engines.bench.byLabel")}</h3>
                    <ScoresTable
                      rows={Object.entries(selected.by_label)}
                      names={data.labels}
                      heading={t("engines.col.type")}
                    />
                    {Object.keys(selected.categories).length > 0 ? (
                      <>
                        <h3>{t("engines.bench.byCategory")}</h3>
                        <ScoresTable
                          rows={Object.entries(selected.categories)}
                          names={data.categories}
                          heading={t("engines.col.category")}
                        />
                      </>
                    ) : null}
                  </>
                ) : null}
              </>
            )}
          </section>
        </>
      )}
    </AppShell>
  );
}
