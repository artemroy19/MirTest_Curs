import { useState } from "react";
import { apiClient } from "../../../api/client";
import { Modal } from "../../common/Modal/Modal";

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

export function ChangePasswordModal({ isOpen, onClose, onSuccess }: Props) {
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  if (!isOpen) {
    return null;
  }

  const handleSubmit = async () => {
    setError("");

    if (newPassword !== confirmPassword) {
      setError("Пароли не совпадают");
      return;
    }

    if (newPassword.length < 6) {
      setError("Пароль должен содержать минимум 6 символов");
      return;
    }

    setIsLoading(true);
    try {
      await apiClient.post("/auth/change-password/", {
        old_password: oldPassword,
        new_password: newPassword
      });
      onClose();
      setOldPassword("");
      setNewPassword("");
      setConfirmPassword("");
      onSuccess?.();
    } catch (err: any) {
      setError(err.response?.data?.old_password?.[0] || err.response?.data?.detail || "Неверный текущий пароль");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      title="Смена пароля"
      description="Введите текущий пароль и задайте новый."
      onClose={onClose}
      actions={
        <>
          <button type="button" className="button button-secondary" onClick={onClose}>
            Отмена
          </button>
          <button type="button" className="button button-primary" onClick={handleSubmit} disabled={isLoading}>
            {isLoading ? "Сохранение..." : "Сохранить"}
          </button>
        </>
      }
    >
      <div className="ui-form">
        <label className="form-field">
          <span>Текущий пароль</span>
          <input type="password" value={oldPassword} onChange={(event) => setOldPassword(event.target.value)} />
        </label>
        <label className="form-field">
          <span>Новый пароль</span>
          <input type="password" value={newPassword} onChange={(event) => setNewPassword(event.target.value)} />
        </label>
        <label className="form-field">
          <span>Подтверждение нового пароля</span>
          <input type="password" value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} />
        </label>
        {error ? <div className="ui-error">{error}</div> : null}
      </div>
    </Modal>
  );
}
