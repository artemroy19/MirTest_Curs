import { ChangeEvent, FormEvent, useEffect, useRef, useState } from "react";

import { apiClient } from "../../api/client";
import { formatError } from "../../utils/formatError";
import { useSessionStore } from "../../store/sessionStore";
import { SectionHeader } from "../../components/layout/SectionHeader/SectionHeader";
import { ChangePasswordModal } from "../../components/profile/ChangePasswordModal/ChangePasswordModal";
import styles from "./ProfilePage.module.css";

export function ProfilePage() {
  const user = useSessionStore((s) => s.user);
  const [firstName, setFirstName] = useState(user?.first_name || "");
  const [lastName, setLastName] = useState(user?.last_name || "");
  const [email] = useState(user?.email || "");
  const [role] = useState(user?.role || "student");
  const [selectedAvatar, setSelectedAvatar] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(user?.avatar || null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [isPasswordModalOpen, setPasswordModalOpen] = useState(false);

  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const tokens = useSessionStore((s) => s.tokens);
  const setSession = useSessionStore((s) => s.setSession);

  useEffect(() => {
    setFirstName(user?.first_name || "");
    setLastName(user?.last_name || "");
    setPreviewUrl(user?.avatar || null);
  }, [user]);

  async function handleSave(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setMessage("");
    setLoading(true);

    try {
      const formData = new FormData();
      formData.append("first_name", firstName);
      formData.append("last_name", lastName);
      if (selectedAvatar) {
        formData.append("avatar_file", selectedAvatar);
      }

      const response = await apiClient.patch(`/auth/profile/`, formData);
      setMessage("Профиль сохранен.");
      setSelectedAvatar(null);
      setPreviewUrl(response.data.avatar || null);
      if (user && tokens) {
        setSession({
          user: response.data,
          access: tokens.access,
          refresh: tokens.refresh
        });
      }
    } catch (error: any) {
      setError(formatError(error, "Не удалось сохранить данные профиля."));
    } finally {
      setLoading(false);
    }
  }

  function handleSelectAvatar() {
    fileInputRef.current?.click();
  }

  function handleAvatarChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setSelectedAvatar(file);
    setPreviewUrl(URL.createObjectURL(file));
  }

  async function handleDeleteAvatar() {
    try {
      const response = await apiClient.patch("/auth/profile/", { avatar_file: null });
      setPreviewUrl(null);
      if (user && tokens) {
        setSession({
          user: { ...response.data, avatar: null },
          access: tokens.access,
          refresh: tokens.refresh
        });
      }
    } catch (error) {
      setError(formatError(error, "Не удалось удалить фото."));
    }
  }

  return (
    <div>
      <SectionHeader title="Мой профиль" description="Редактирование персональных данных и смена пароля." />
      
      <div className={styles.container}>
        {/* Основная карточка с данными профиля */}
        <section className={styles.profileCard}>
          <div className={styles.profileHeader}>
            <div className={styles.avatarSection}>
              {previewUrl ? (
                <img src={previewUrl} alt="Аватар" className={styles.avatarImage} />
              ) : (
                <div className={styles.avatarPlaceholder}>
                  {firstName?.[0] || ""}{lastName?.[0] || ""}
                </div>
              )}
              <button type="button" className={styles.avatarButton} onClick={handleSelectAvatar}>
                Загрузить фото
              </button>
              {user?.avatar && (
                <button type="button" onClick={handleDeleteAvatar} className={styles.deleteAvatarBtn}>
                  Удалить фото
                </button>
              )}
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                className={styles.hiddenFileInput}
                onChange={handleAvatarChange}
              />
            </div>

            <div className={styles.infoSection}>
              <form className={styles.form} onSubmit={handleSave}>
                <div className={styles.nameRow}>
                  <div className={styles.field}>
                    <label>Имя</label>
                    <input 
                      value={firstName} 
                      onChange={(e) => setFirstName(e.target.value)} 
                      required 
                      placeholder="Введите имя"
                    />
                  </div>
                  <div className={styles.field}>
                    <label>Фамилия</label>
                    <input 
                      value={lastName} 
                      onChange={(e) => setLastName(e.target.value)} 
                      required 
                      placeholder="Введите фамилию"
                    />
                  </div>
                </div>

                <div className={styles.field}>
                  <label>Email</label>
                  <input value={email} readOnly className={styles.readonly} />
                </div>

                <div className={styles.field}>
                  <label>Роль</label>
                  <input value={role === "student" ? "Студент" : "Преподаватель"} readOnly className={styles.readonly} />
                </div>

                {error && <div className={styles.alert}>{error}</div>}
                {message && <div className={styles.success}>{message}</div>}

                <button type="submit" className="button button-primary button-full" disabled={loading}>
                  {loading ? "Сохранение..." : "Сохранить изменения"}
                </button>
              </form>
            </div>
          </div>

          {/* Кнопка смены пароля внизу карточки */}
          <div className={styles.passwordSection}>
            <div className={styles.passwordDivider}></div>
            <div className={styles.passwordContent}>
              <div className={styles.passwordText}>
                <h4>Безопасность аккаунта</h4>
                <p>Измените пароль, чтобы защитить свой аккаунт</p>
              </div>
              <button 
                type="button" 
                className="button button-secondary" 
                onClick={() => setPasswordModalOpen(true)}
              >
                Сменить пароль
              </button>
            </div>
          </div>
        </section>
      </div>

      <ChangePasswordModal
        isOpen={isPasswordModalOpen}
        onClose={() => setPasswordModalOpen(false)}
        onSuccess={() => setMessage("Пароль успешно изменен.")}
      />
    </div>
  );
}
