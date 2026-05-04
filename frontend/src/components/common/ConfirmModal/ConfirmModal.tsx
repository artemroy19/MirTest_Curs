import { Modal } from "../Modal/Modal";

type Props = {
  isOpen: boolean;
  title: string;
  description: string;
  confirmLabel?: string;
  cancelLabel?: string;
  onCancel: () => void;
  onConfirm: () => void;
  danger?: boolean;
};

export function ConfirmModal({
  isOpen,
  title,
  description,
  confirmLabel = "Подтвердить",
  cancelLabel = "Отмена",
  onCancel,
  onConfirm,
  danger = false
}: Props) {
  return (
    <Modal
      isOpen={isOpen}
      title={title}
      onClose={onCancel}
      size="small"
      actions={
        <>
          <button type="button" className="button button-secondary" onClick={onCancel}>
            {cancelLabel}
          </button>
          <button
            type="button"
            className={`button ${danger ? "button-danger" : "button-primary"}`}
            onClick={onConfirm}
          >
            {confirmLabel}
          </button>
        </>
      }
    >
      <p style={{ margin: 0, color: "#64748b", lineHeight: 1.6 }}>{description}</p>
    </Modal>
  );
}
