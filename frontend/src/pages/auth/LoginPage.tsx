import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { apiClient } from "../../api/client";
import { useSessionStore } from "../../store/sessionStore";
import { getDefaultRoute } from "../../utils/routes";
import styles from "./LoginPage.module.css";

export function LoginPage() {
  const navigate = useNavigate();
  const setSession = useSessionStore((s) => s.setSession);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setLoading(true);

    try {
      const response = await apiClient.post("/auth/login/", { email, password });
      setSession({
        user: response.data.user,
        access: response.data.access,
        refresh: response.data.refresh
      });
      navigate(getDefaultRoute(response.data.user?.role));
    } catch (error: any) {
      setError(error.response?.data?.detail || "Не удалось войти. Проверьте данные.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="ui-auth-shell">
      <section className="ui-auth-card">
        <span className="ui-auth-badge">MirTest</span>
        <h1>Вход MirTest</h1>
        <p>Войдите в образовательную платформу для студентов и преподавателей</p>

        <form className={styles.form} onSubmit={handleSubmit}>
          <input type="email" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          <div className={styles.passwordRow}>
            <input
              type={showPassword ? "text" : "password"}
              placeholder="Пароль"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
            <button type="button" className={styles.eyeButton} onClick={() => setShowPassword((value) => !value)}>
              {showPassword ? "Скрыть" : "Показать"}
            </button>
          </div>
          {error && <div className={styles.error}>{error}</div>}
          <button type="submit" disabled={loading} className="button button-primary button-full">
            {loading ? "Вход..." : "Войти"}
          </button>
        </form>

        <div className={styles.footerLinks}>
          <Link to="/register" className={styles.smallLink}>Регистрация</Link>
        </div>
      </section>
    </div>
  );
}
