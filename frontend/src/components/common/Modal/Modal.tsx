import { ReactNode } from "react";
import styles from "./Modal.module.css";

type Props = {
  isOpen: boolean;
  title: string;
  description?: string;
  children: ReactNode;
  actions?: ReactNode;
  onClose: () => void;
  size?: "default" | "small";
};

export function Modal({ isOpen, title, description, children, actions, onClose, size = "default" }: Props) {
  if (!isOpen) return null;

  return (
    <div className={styles.modalOverlay} onClick={onClose}>
      <div className={`${styles.modalContent} ${size === "small" ? styles.modalContentSmall : ""}`} onClick={(event) => event.stopPropagation()}>
        <div className={styles.modalHeader}>
          <div>
            <h2 className={styles.modalTitle}>{title}</h2>
            {description ? <p className={styles.modalDescription}>{description}</p> : null}
          </div>
          <button type="button" className={styles.closeButton} onClick={onClose} aria-label="Закрыть">
            ×
          </button>
        </div>
        <div className={styles.modalBody}>{children}</div>
        {actions ? <div className={styles.modalFooter}>{actions}</div> : null}
      </div>
    </div>
  );
}
