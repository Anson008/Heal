import type { ReactNode } from "react";
import "./modal.css";

function Modal({
  open,
  onClose,
  title,
  children,
}: {
  open: boolean;
  onClose: () => void;
  title?: string;
  children: ReactNode;
}) {
  if (!open) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-box" onClick={(e) => e.stopPropagation()}>
        {title && <h2 className="modal-title">{title}</h2>}
        <div className="modal-content">{children}</div>
        <button type="button" className="modal-close" onClick={onClose}>
          Close
        </button>
      </div>
    </div>
  );
}

export default Modal;
