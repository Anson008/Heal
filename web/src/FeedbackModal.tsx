import Modal from "./Modal";

const FEEDBACK_FORM_URL =
  "https://docs.google.com/forms/d/e/1FAIpQLSciTQPKkc485AlSWaZe0KEaLyjRSa4VX3PxEcYzYeoxAYZdrg/viewform?usp=publish-editor";

function FeedbackModal({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  return (
    <Modal open={open} onClose={onClose} title="Feedback">
      <p>
        Have feedback or run into a problem? Let us know:{" "}
        <a href={FEEDBACK_FORM_URL} target="_blank" rel="noopener noreferrer">
          https://forms.google.com/
        </a>
      </p>
    </Modal>
  );
}

export default FeedbackModal;
