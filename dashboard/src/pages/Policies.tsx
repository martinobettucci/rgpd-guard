// @spec docs/BACKLOG.md#RG-015 | docs/BACKLOG.md#RG-010 | docs/DESIGN_SYSTEM.md#6.27 | docs/DESIGN_SYSTEM.md#6.22 | docs/DESIGN_SYSTEM.md#6.23 | docs/DESIGN_SYSTEM_APP.md#composants
// Politiques : fenêtre en lecture découpée en sections, modale par section (DS §6.27), rétablissement confirmé dans le flux.
import { Pencil, RotateCcw } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { useAuth } from "../auth";
import { AppShell } from "../components/AppShell";
import { Alert } from "../components/ui/Alert";
import { Badge } from "../components/ui/Badge";
import { Modal } from "../components/ui/Modal";
import { Skeleton } from "../components/ui/Skeleton";
import { t, tOr, type MessageKey } from "../i18n";
import { api, ApiError, type Policy, type PolicyResponse } from "../lib/api";
import { formatScore } from "../lib/format";

type Section = "labels" | "categories" | "allowlist" | "secretFiles";
const PROMPT_ACTIONS = ["block", "warn", "allow"];
const OUTPUT_ACTIONS = ["pseudonymize", "allow"];
const CATEGORY_ACTIONS = ["block_if_identifier", "warn", "allow"];

const actionLabel = (value: string) => tOr(`action.${value}`, "action.allow");
const lines = (text: string) =>
  text
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);

function SectionHeader({ id, title, onEdit }: { id: string; title: string; onEdit: () => void }) {
  return (
    <div className="card-header">
      <h2 id={id}>{title}</h2>
      <button type="button" className="btn btn-compact" onClick={onEdit} aria-label={`${t("common.edit")} : ${title}`}>
        <Pencil size={16} aria-hidden="true" />
        {t("common.edit")}
      </button>
    </div>
  );
}

function LineList({ items }: { items: string[] }) {
  if (items.length === 0) return <p className="muted">{t("policies.none")}</p>;
  return (
    <ul className="chips">
      {items.map((item) => (
        <li key={item} className="badge badge-neutral mono">
          {item}
        </li>
      ))}
    </ul>
  );
}

export function Policies() {
  const { expire } = useAuth();
  const [data, setData] = useState<PolicyResponse | null>(null);
  const [loadError, setLoadError] = useState(false);
  const [editing, setEditing] = useState<Section | null>(null);
  const [draft, setDraft] = useState<Policy | null>(null);
  const [texts, setTexts] = useState({ values: "", patterns: "", secrets: "", exceptions: "" });
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<ApiError | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [confirmReset, setConfirmReset] = useState(false);
  const resetButton = useRef<HTMLButtonElement>(null);
  const confirmRef = useRef<HTMLDivElement>(null);

  const load = useCallback(async () => {
    try {
      setData(await api.policy());
    } catch (exc) {
      if (exc instanceof ApiError && exc.status === 401) expire();
      else setLoadError(true);
    }
  }, [expire]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (confirmReset) confirmRef.current?.querySelector<HTMLButtonElement>("button")?.focus();
  }, [confirmReset]);

  const open = (section: Section) => {
    if (!data) return;
    const copy = structuredClone(data.policy);
    setDraft(copy);
    setTexts({
      values: copy.allowlist.values.join("\n"),
      patterns: copy.allowlist.patterns.join("\n"),
      secrets: copy.secret_files.join("\n"),
      exceptions: copy.secret_files_exceptions.join("\n"),
    });
    setSaveError(null);
    setNotice(null);
    setEditing(section);
  };

  const save = async () => {
    if (!draft) return;
    const policy: Policy = {
      ...draft,
      allowlist: { values: lines(texts.values), patterns: lines(texts.patterns) },
      secret_files: lines(texts.secrets),
      secret_files_exceptions: lines(texts.exceptions),
    };
    setSaving(true);
    setSaveError(null);
    try {
      const response = await api.savePolicy(policy);
      setData((current) => (current ? { ...current, policy: response.policy, source: response.source } : current));
      setEditing(null);
      setNotice(t("common.saved"));
    } catch (exc) {
      if (exc instanceof ApiError && exc.status === 401) expire();
      else setSaveError(exc instanceof ApiError ? exc : new ApiError(0, t("common.error")));
    } finally {
      setSaving(false);
    }
  };

  const reset = async () => {
    try {
      const response = await api.resetPolicy();
      setData((current) => (current ? { ...current, policy: response.policy, source: response.source } : current));
      setNotice(t("policies.reset.done"));
    } catch (exc) {
      if (exc instanceof ApiError && exc.status === 401) expire();
      else setLoadError(true);
    } finally {
      setConfirmReset(false);
      resetButton.current?.focus();
    }
  };

  const titles: Record<Section, MessageKey> = {
    labels: "policies.labels",
    categories: "policies.categories",
    allowlist: "policies.allowlist",
    secretFiles: "policies.secretFiles",
  };

  if (loadError) {
    return (
      <AppShell title={t("policies.title")}>
        <Alert kind="danger">{t("common.error")}</Alert>
      </AppShell>
    );
  }
  if (!data) {
    return (
      <AppShell title={t("policies.title")}>
        <section className="card">
          <Skeleton lines={6} />
        </section>
      </AppShell>
    );
  }
  const { policy } = data;

  return (
    <AppShell
      title={t("policies.title")}
      actions={
        <Badge tone={data.source === "custom" ? "accent" : "neutral"}>
          {data.source === "custom" ? t("policies.source.custom") : t("policies.source.default")}
        </Badge>
      }
    >
      {notice ? <Alert kind="success">{notice}</Alert> : null}

      <section className="card" aria-labelledby="sec-labels">
        <SectionHeader id="sec-labels" title={t("policies.labels")} onEdit={() => open("labels")} />
        <div className="table-scroll">
          <table className="data">
            <thead>
              <tr>
                <th scope="col">{t("policies.col.type")}</th>
                <th scope="col">{t("policies.col.prompt")}</th>
                <th scope="col">{t("policies.col.output")}</th>
                <th scope="col" className="num">
                  {t("policies.col.minScore")}
                </th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(policy.labels).map(([code, rule]) => (
                <tr key={code}>
                  <td>{data.labels[code] ?? code}</td>
                  <td>{actionLabel(rule.prompt)}</td>
                  <td>{actionLabel(rule.tool_output)}</td>
                  <td className="num mono">{formatScore(rule.min_score)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="card" aria-labelledby="sec-categories">
        <SectionHeader id="sec-categories" title={t("policies.categories")} onEdit={() => open("categories")} />
        <div className="table-scroll">
          <table className="data">
            <thead>
              <tr>
                <th scope="col">{t("policies.col.category")}</th>
                <th scope="col" className="num">
                  {t("policies.col.threshold")}
                </th>
                <th scope="col">{t("policies.col.action")}</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(policy.categories).map(([code, rule]) => (
                <tr key={code}>
                  <td>{data.categories[code] ?? code}</td>
                  <td className="num mono">{formatScore(rule.threshold)}</td>
                  <td>{actionLabel(rule.action)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <div className="grid-2">
        <section className="card" aria-labelledby="sec-allowlist">
          <SectionHeader id="sec-allowlist" title={t("policies.allowlist")} onEdit={() => open("allowlist")} />
          <h3>{t("policies.allowlist.values")}</h3>
          <LineList items={policy.allowlist.values} />
          <h3>{t("policies.allowlist.patterns")}</h3>
          <LineList items={policy.allowlist.patterns} />
        </section>
        <section className="card" aria-labelledby="sec-secrets">
          <SectionHeader id="sec-secrets" title={t("policies.secretFiles")} onEdit={() => open("secretFiles")} />
          <h3>{t("policies.secretFiles.patterns")}</h3>
          <LineList items={policy.secret_files} />
          <h3>{t("policies.secretFiles.exceptions")}</h3>
          <LineList items={policy.secret_files_exceptions} />
        </section>
      </div>

      <section className="card">
        {confirmReset ? (
          <div className="confirm" ref={confirmRef}>
            <p>{t("policies.reset.confirm")}</p>
            <div className="btn-group">
              <button type="button" className="btn btn-danger" onClick={() => void reset()}>
                <RotateCcw size={18} aria-hidden="true" />
                {t("policies.reset.do")}
              </button>
              <button
                type="button"
                className="btn"
                onClick={() => {
                  setConfirmReset(false);
                  resetButton.current?.focus();
                }}
              >
                {t("common.cancel")}
              </button>
            </div>
          </div>
        ) : (
          <div>
            <button
              ref={resetButton}
              type="button"
              className="btn"
              onClick={() => setConfirmReset(true)}
              disabled={data.source === "default"}
              aria-describedby={data.source === "default" ? "reset-help" : undefined}
            >
              <RotateCcw size={18} aria-hidden="true" />
              {t("policies.reset")}
            </button>
            {data.source === "default" ? (
              <p id="reset-help" className="help">
                {t("policies.reset.unavailable")}
              </p>
            ) : null}
          </div>
        )}
      </section>

      <Modal
        title={editing ? t(titles[editing]) : ""}
        open={editing !== null}
        onClose={() => setEditing(null)}
        onSubmit={() => void save()}
        submitting={saving}
        submitLabel={t("common.save")}
        error={
          saveError ? (
            <Alert kind="danger">
              <p>{t("policies.saveError")}</p>
              {saveError.details.length > 0 ? (
                <ul>
                  {saveError.details.map((detail, index) => (
                    <li key={index}>
                      <span className="mono">{detail.champ}</span> : {detail.message}
                    </li>
                  ))}
                </ul>
              ) : (
                <p>{saveError.message}</p>
              )}
            </Alert>
          ) : null
        }
      >
        {draft && editing === "labels" ? (
          <div className="table-scroll">
            <table className="data">
              <thead>
                <tr>
                  <th scope="col">{t("policies.col.type")}</th>
                  <th scope="col">{t("policies.col.prompt")}</th>
                  <th scope="col">{t("policies.col.output")}</th>
                  <th scope="col">{t("policies.col.minScore")}</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(draft.labels).map(([code, rule]) => {
                  const name = data.labels[code] ?? code;
                  const update = (patch: Partial<typeof rule>) =>
                    setDraft({ ...draft, labels: { ...draft.labels, [code]: { ...rule, ...patch } } });
                  return (
                    <tr key={code}>
                      <td>{name}</td>
                      <td>
                        <select
                          className="select"
                          aria-label={`${t("policies.col.prompt")} : ${name}`}
                          value={rule.prompt}
                          onChange={(event) => update({ prompt: event.target.value })}
                        >
                          {PROMPT_ACTIONS.map((value) => (
                            <option key={value} value={value}>
                              {actionLabel(value)}
                            </option>
                          ))}
                        </select>
                      </td>
                      <td>
                        <select
                          className="select"
                          aria-label={`${t("policies.col.output")} : ${name}`}
                          value={rule.tool_output}
                          onChange={(event) => update({ tool_output: event.target.value })}
                        >
                          {OUTPUT_ACTIONS.map((value) => (
                            <option key={value} value={value}>
                              {actionLabel(value)}
                            </option>
                          ))}
                        </select>
                      </td>
                      <td>
                        <input
                          className="input mono"
                          type="number"
                          min={0}
                          max={1}
                          step={0.05}
                          aria-label={`${t("policies.col.minScore")} : ${name}`}
                          value={rule.min_score}
                          onChange={(event) => update({ min_score: Number(event.target.value) })}
                        />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : null}

        {draft && editing === "categories" ? (
          <div className="list-rows">
            {Object.entries(draft.categories).map(([code, rule]) => {
              const name = data.categories[code] ?? code;
              const update = (patch: Partial<typeof rule>) =>
                setDraft({ ...draft, categories: { ...draft.categories, [code]: { ...rule, ...patch } } });
              return (
                <fieldset key={code} className="field" style={{ border: 0, padding: 0, margin: 0 }}>
                  <legend>{name}</legend>
                  <div className="form-row">
                    <div className="field" style={{ flex: 1, minWidth: 200 }}>
                      <label htmlFor={`threshold-${code}`}>
                        {t("policies.col.threshold")} : <span className="mono">{formatScore(rule.threshold)}</span>
                      </label>
                      <input
                        id={`threshold-${code}`}
                        type="range"
                        min={0}
                        max={1}
                        step={0.05}
                        value={rule.threshold}
                        aria-valuetext={formatScore(rule.threshold)}
                        onChange={(event) => update({ threshold: Number(event.target.value) })}
                        style={{ minHeight: 40 }}
                      />
                      <span className="help mono">0,00 · 1,00</span>
                    </div>
                    <div className="field">
                      <label htmlFor={`action-${code}`}>{t("policies.col.action")}</label>
                      <select
                        id={`action-${code}`}
                        className="select"
                        value={rule.action}
                        onChange={(event) => update({ action: event.target.value })}
                      >
                        {CATEGORY_ACTIONS.map((value) => (
                          <option key={value} value={value}>
                            {actionLabel(value)}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>
                </fieldset>
              );
            })}
          </div>
        ) : null}

        {editing === "allowlist" ? (
          <>
            <div className="field">
              <label htmlFor="allow-values">{t("policies.allowlist.values")}</label>
              <textarea
                id="allow-values"
                className="textarea mono"
                value={texts.values}
                onChange={(event) => setTexts({ ...texts, values: event.target.value })}
                aria-describedby="allow-values-help"
              />
              <p id="allow-values-help" className="help">
                {t("policies.allowlist.values.help")}
              </p>
            </div>
            <div className="field">
              <label htmlFor="allow-patterns">{t("policies.allowlist.patterns")}</label>
              <textarea
                id="allow-patterns"
                className="textarea mono"
                value={texts.patterns}
                onChange={(event) => setTexts({ ...texts, patterns: event.target.value })}
                aria-describedby="allow-patterns-help"
              />
              <p id="allow-patterns-help" className="help">
                {t("policies.allowlist.patterns.help")}
              </p>
            </div>
          </>
        ) : null}

        {editing === "secretFiles" ? (
          <>
            <div className="field">
              <label htmlFor="secret-patterns">{t("policies.secretFiles.patterns")}</label>
              <textarea
                id="secret-patterns"
                className="textarea mono"
                value={texts.secrets}
                onChange={(event) => setTexts({ ...texts, secrets: event.target.value })}
                aria-describedby="secret-help"
              />
            </div>
            <div className="field">
              <label htmlFor="secret-exceptions">{t("policies.secretFiles.exceptions")}</label>
              <textarea
                id="secret-exceptions"
                className="textarea mono"
                value={texts.exceptions}
                onChange={(event) => setTexts({ ...texts, exceptions: event.target.value })}
                aria-describedby="secret-help"
              />
              <p id="secret-help" className="help">
                {t("policies.lines.help")}
              </p>
            </div>
          </>
        ) : null}
      </Modal>
    </AppShell>
  );
}
