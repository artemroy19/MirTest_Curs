import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { apiClient } from "../../api/client";
import { formatError } from "../../utils/formatError";
import { useSessionStore } from "../../store/sessionStore";
import { getDefaultRoute } from "../../utils/routes";
import styles from "./LoginPage.module.css";

export function RegisterPage() {
  const navigate = useNavigate();
  const setSession = useSessionStore((s) => s.setSession);

  const [email, setEmail] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [role, setRole] = useState<"student" | "teacher">("student");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");

    if (password.length < 8) {
      setError("Пароль должен содержать минимум 8 символов.");
      return;
    }

    if (password !== confirmPassword) {
      setError("Пароли не совпадают.");
      return;
    }

    setLoading(true);

    try {
      const username = email.split("@")[0];
      
      const response = await apiClient.post("/auth/register/", {
        email,
        password,
        username,
        first_name: firstName,
        last_name: lastName,
        role
      });

      setSession({
        user: response.data.user,
        access: response.data.access,
        refresh: response.data.refresh
      });
      navigate(getDefaultRoute(response.data.user?.role));
    } catch (error: any) {
      setError(formatError(error, "Не удалось зарегистрироваться"));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="ui-auth-shell">
      <section className="ui-auth-card">
        <span className="ui-auth-badge">MirTest</span>
        <h1>Регистрация в MirTest</h1>
        <p>Создайте аккаунт ученика или преподавателя и начните работу с платформой</p>

        <form className={styles.form} onSubmit={handleSubmit}>
          <div className={styles.nameRow}>
            <input 
              type="text" 
              placeholder="Фамилия" 
              value={lastName} 
              onChange={(e) => setLastName(e.target.value)} 
              required 
            />
            <input 
              type="text" 
              placeholder="Имя" 
              value={firstName} 
              onChange={(e) => setFirstName(e.target.value)} 
              required 
            />
          </div>
          <input type="email" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          <input type="password" placeholder="Пароль" value={password} onChange={(e) => setPassword(e.target.value)} required />
          <div className={styles.passwordRow}>
            <input
              type="password"
              placeholder="Подтверждение пароля"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
            />
          </div>
          <select value={role} onChange={(e) => setRole(e.target.value as "student" | "teacher")}> 
            <option value="student">Студент</option>
            <option value="teacher">Преподаватель</option>
          </select>

          {error && <div className={styles.error}>{error}</div>}

          <button type="submit" className="button button-primary button-full" disabled={loading}>
            {loading ? "Создание..." : "Зарегистрироваться"}
          </button>
        </form>

        <p style={{ marginTop: 14, textAlign: "center" }}>
          <Link to="/login">  Уже есть аккаунт? Войти</Link>
        </p>
      </section>
    </div>
  );
}
