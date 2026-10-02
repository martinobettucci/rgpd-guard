// @spec docs/BACKLOG.md#RG-015 | docs/DESIGN_SYSTEM.md
// Modale limitée à une section : dialog natif, focus entrant puis rendu au déclencheur, Échap = annulation (DS §6.27).
import { useEffect, useRef, type FormEvent, type ReactNode } from "react";
import { t } from "../../i18n";

interface ModalProps {
  title: string;
  open: boolean;
  onClose: () => void;
  onSubmit: () => void;
  submitting: boolean;
  submitLabel: string;
  children: ReactNode;
  error?: ReactNode;
}

export function Modal({ title, open, onClose, onSubmit, submitting, submitLabel, children, error }: ModalProps) {
  const ref = useRef<HTMLDialogElement>(null);
  const opener = useRef<Element | null>(null);

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) {
      opener.current = document.activeElement;
      dialog.showModal();
      const first = dialog.querySelector<HTMLElement>("input:not([readonly]), select, textarea, button");
      first?.focus();
    } else if (!open && dialog.open) {
      dialog.close();
      (opener.current as HTMLElement | null)?.focus();
    }
  }, [open]);

  const submit = (event: FormEvent) => {
    event.preventDefault();
    onSubmit();
  };

  return (
    <dialog
      ref={ref}
      className="modal"
      aria-labelledby="modal-title"
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
    >
      <form onSubmit={submit}>
        <div className="modal-body">
          <h2 id="modal-title">{title}</h2>
          {children}
          {error}
        </div>
        <div className="modal-footer">
          <button type="button" className="btn" onClick={onClose}>
            {t("common.cancel")}
          </button>
          <button type="submit" className="btn btn-primary" disabled={submitting}>
            {submitting ? t("common.saving") : submitLabel}
          </button>
        </div>
      </form>
    </dialog>
  );
}
