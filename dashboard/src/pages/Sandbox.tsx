// @spec docs/BACKLOG.md#RG-014 | docs/DESIGN_SYSTEM.md | docs/DESIGN_SYSTEM_APP.md
// Bac à sable : analyse d'un texte saisi, rendu annoté, version pseudonymisée, latences par composant.
import { ScanSearch } from "lucide-react";
import { useState, type FormEvent, type ReactNode } from "react";
import { useAuth } from "../auth";
import { AppShell } from "../components/AppShell";
import { DecisionBadge } from "../components/DecisionBadge";
import { Alert } from "../components/ui/Alert";
import { t, tOr } from "../i18n";
import { api, ApiError, type Analysis } from "../lib/api";
import { markClass } from "../lib/decisions";
import { formatMs, formatScore } from "../lib/format";

const PROFILES = ["rapide", "equilibre", "max"];
const CONTEXTS = ["prompt", "tool_output"];

export function AnnotatedText({ text, analysis }: { text: string; analysis: Analysis }) {
  const parts: ReactNode[] = [];
  let cursor = 0;
  [...analysis.findings]
    .sort((a, b) => a.start - b.start)
    .forEach((finding, index) => {
      if (finding.start < cursor) return;
      parts.push(text.slice(cursor, finding.start));
      parts.push(
        <mark key={index} className={markClass(finding.action)}>
          {text.slice(finding.start, finding.end)}
          <span className="mark-label">[{finding.name}]</span>
        </mark>,
      );
      cursor = finding.end;
    });
  parts.push(text.slice(cursor));
  return <div className="annotated">{parts}</div>;
}

export function Sandbox() {
  const { expire } = useAuth();
  const [text, setText] = useState("");
  const [profile, setProfile] = useState("equilibre");
  const [context, setContext] = useState("prompt");
  const [result, setResult] = useState<{ text: string; analysis: Analysis } | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState(false);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!text.trim()) return;
    setPending(true);
    setError(false);
    try {
      const analysis = await api.analyze(text, profile, context);
      setResult({ text, analysis });
    } catch (exc) {
      if (exc instanceof ApiError && exc.status === 401) expire();
      else setError(true);
    } finally {
      setPending(false);
    }
  };

  return (
    <AppShell title={t("sandbox.title")}>
      <section className="card">
        <form onSubmit={submit} className="field" style={{ gap: 16 }}>
          <div className="field">
            <label htmlFor="sandbox-text">{t("sandbox.input")}</label>
            <textarea
              id="sandbox-text"
              className="textarea"
              value={text}
              onChange={(event) => setText(event.target.value)}
              aria-describedby="sandbox-help"
            />
            <p id="sandbox-help" className="help">
              {t("sandbox.input.help")}
            </p>
          </div>
          <div className="form-row">
            <div className="field">
              <label htmlFor="sandbox-profile">{t("sandbox.profile")}</label>
              <select
                id="sandbox-profile"
                className="select"
                value={profile}
                onChange={(event) => setProfile(event.target.value)}
              >
                {PROFILES.map((value) => (
                  <option key={value} value={value}>
                    {tOr(`profile.${value}`, "profile.equilibre")}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label htmlFor="sandbox-context">{t("sandbox.context")}</label>
              <select
                id="sandbox-context"
                className="select"
                value={context}
                onChange={(event) => setContext(event.target.value)}
              >
                {CONTEXTS.map((value) => (
                  <option key={value} value={value}>
                    {tOr(`sandbox.context.${value}`, "sandbox.context.prompt")}
                  </option>
                ))}
              </select>
            </div>
            <button type="submit" className="btn btn-primary" disabled={pending || !text.trim()}>
              <ScanSearch size={18} aria-hidden="true" />
              {pending ? t("sandbox.analyzing") : t("sandbox.analyze")}
            </button>
          </div>
        </form>
        {error ? <Alert kind="danger">{t("common.error")}</Alert> : null}
      </section>

      <section className="card" aria-labelledby="result-title" aria-live="polite">
        <div className="card-header">
          <h2 id="result-title">{t("sandbox.result")}</h2>
          {result ? <DecisionBadge decision={result.analysis.decision} /> : null}
        </div>
        {result === null ? (
          <p className="empty">{t("sandbox.empty")}</p>
        ) : (
          <>
            {result.analysis.partial ? <Alert kind="info">{t("sandbox.partial")}</Alert> : null}
            <h3>{t("sandbox.annotated")}</h3>
            <AnnotatedText text={result.text} analysis={result.analysis} />
            <h3>{t("sandbox.pseudonymized")}</h3>
            <pre className="pseudonymized">{result.analysis.pseudonymized}</pre>

            <h3>{t("sandbox.findings")}</h3>
            {result.analysis.findings.length === 0 ? (
              <p className="muted">{t("sandbox.findings.empty")}</p>
            ) : (
              <div className="table-scroll">
                <table className="data">
                  <thead>
                    <tr>
                      <th scope="col">{t("sandbox.col.type")}</th>
                      <th scope="col">{t("sandbox.col.preview")}</th>
                      <th scope="col">{t("sandbox.col.detector")}</th>
                      <th scope="col" className="num">
                        {t("sandbox.col.score")}
                      </th>
                      <th scope="col">{t("sandbox.col.action")}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.analysis.findings.map((finding, index) => (
                      <tr key={index}>
                        <td>{finding.name}</td>
                        <td className="mono">{finding.preview}</td>
                        <td className="mono">{finding.detector}</td>
                        <td className="num mono">{formatScore(finding.score)}</td>
                        <td>
                          <DecisionBadge decision={finding.action} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            <h3>{t("sandbox.categories")}</h3>
            {result.analysis.categories.length === 0 ? (
              <p className="muted">{t("sandbox.categories.empty")}</p>
            ) : (
              <div className="table-scroll">
                <table className="data">
                  <thead>
                    <tr>
                      <th scope="col">{t("sandbox.col.category")}</th>
                      <th scope="col" className="num">
                        {t("sandbox.col.probability")}
                      </th>
                      <th scope="col">{t("sandbox.col.action")}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.analysis.categories.map((category) => (
                      <tr key={category.category}>
                        <td>{category.name}</td>
                        <td className="num mono">{formatScore(category.probability)}</td>
                        <td>
                          <DecisionBadge decision={category.action} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            <h3>{t("sandbox.timings")}</h3>
            <dl className="pairs">
              {Object.entries(result.analysis.timings_ms).map(([name, ms]) => (
                <div key={name} style={{ display: "contents" }}>
                  <dt className="mono">{name}</dt>
                  <dd className="mono">{formatMs(ms)}</dd>
                </div>
              ))}
            </dl>
          </>
        )}
      </section>
    </AppShell>
  );
}
