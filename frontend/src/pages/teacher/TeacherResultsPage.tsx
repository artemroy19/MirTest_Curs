import { useEffect, useMemo, useState } from "react";

import { apiClient } from "../../api/client";
import { EmptyState } from "../../components/common/EmptyState/EmptyState";
import { Modal } from "../../components/common/Modal/Modal";
import { SectionHeader } from "../../components/layout/SectionHeader/SectionHeader";
import { extractList } from "../../utils/extractList";
import styles from "./TeacherResultsPage.module.css";

type TestOption = {
  id: number;
  title: string;
};

type AttemptAnswer = {
  id: number;
  question_title: string;
  question_prompt: string;
  question_type: string;
  question_payload: any;
  answer_payload: any;
  is_correct: boolean | null;
  earned_points: string;
  max_points: string;
  manual_points: string;
  teacher_comment: string;
  reviewed_at: string | null;
};

type Attempt = {
  id: number;
  student_name: string;
  attempt_number: number;
  total_score: string;
  max_score: string;
  is_overdue: boolean;
  essay_review_pending: boolean;
  answers: AttemptAnswer[];
};

type TestStats = {
  assigned_students: number;
  completed_students: number;
  avg_score_pct: number;
  avg_duration_seconds: number | null;
};

function formatDuration(seconds: number | null) {
  if (seconds == null) {
    return "—";
  }
  const minutes = Math.floor(seconds / 60);
  const remain = seconds % 60;
  return `${minutes} мин ${remain} сек`;
}

function formatAnswer(answer: AttemptAnswer) {
  if (answer.question_type === "single") {
    return String(answer.answer_payload?.selected ?? "—");
  }
  if (answer.question_type === "multiple") {
    return Array.isArray(answer.answer_payload?.selected)
      ? answer.answer_payload.selected.join(", ")
      : "—";
  }
  return String(answer.answer_payload?.value ?? "—");
}

function formatCorrectAnswer(answer: AttemptAnswer) {
  const payload = answer.question_payload ?? {};
  if (answer.question_type === "single") {
    return String(payload.correct_option ?? "—");
  }
  if (answer.question_type === "multiple") {
    return Array.isArray(payload.correct_options) ? payload.correct_options.join(", ") : "—";
  }
  if (answer.question_type === "text") {
    return Array.isArray(payload.correct_answers) ? payload.correct_answers.join(", ") : "—";
  }
  return "Проверяется преподавателем";
}

export function TeacherResultsPage() {
  const [tests, setTests] = useState<TestOption[]>([]);
  const [selectedTestId, setSelectedTestId] = useState("");
  const [stats, setStats] = useState<TestStats | null>(null);
  const [attempts, setAttempts] = useState<Attempt[]>([]);
  const [selectedAttempt, setSelectedAttempt] = useState<Attempt | null>(null);
  const [essayScores, setEssayScores] = useState<Record<number, string>>({});
  const [essayComments, setEssayComments] = useState<Record<number, string>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    async function loadTests() {
      setLoading(true);
      setError("");
      try {
        const response = await apiClient.get("/tests/");
        const loadedTests = extractList<TestOption>(response.data);
        setTests(loadedTests);
        if (loadedTests[0]) {
          setSelectedTestId(String(loadedTests[0].id));
        }
      } catch {
        setError("Не удалось загрузить тесты преподавателя.");
      } finally {
        setLoading(false);
      }
    }

    void loadTests();
  }, []);

  async function loadTestResults(testId: string) {
    if (!testId) {
      setStats(null);
      setAttempts([]);
      return;
    }
    try {
      const [statsRes, attemptsRes] = await Promise.all([
        apiClient.get(`/tests/${testId}/stats/`),
        apiClient.get("/attempts/", { params: { test: testId } }),
      ]);
      setStats(statsRes.data);
      setAttempts(extractList(attemptsRes.data));
    } catch {
      setError("Не удалось загрузить статистику и попытки.");
    }
  }

  useEffect(() => {
    void loadTestResults(selectedTestId);
  }, [selectedTestId]);

  const cards = useMemo(
    () => [
      { label: "Назначено студентов", value: String(stats?.assigned_students ?? 0) },
      { label: "Прошли тест", value: String(stats?.completed_students ?? 0) },
      { label: "Средний балл", value: `${stats?.avg_score_pct ?? 0}%` },
      { label: "Среднее время", value: formatDuration(stats?.avg_duration_seconds ?? null) },
    ],
    [stats],
  );

  async function saveEssay(answerId: number) {
    if (!selectedAttempt) {
      return;
    }
    try {
      setError("");
      setSuccess("");
      await apiClient.post(`/attempts/${selectedAttempt.id}/review-essay/`, {
        answer_id: answerId,
        manual_points: Number(essayScores[answerId] ?? 0),
        teacher_comment: essayComments[answerId] ?? "",
      });
      await loadTestResults(selectedTestId);
      const response = await apiClient.get(`/attempts/${selectedAttempt.id}/`);
      setSelectedAttempt(response.data);
      setSuccess("Результаты сохранены.");
    } catch {
      setError("Не удалось сохранить оценку за развёрнутый вопрос.");
    }
  }

  return (
    <div className="ui-page">
      <SectionHeader
        title="Результаты"
        description="Выберите тест, чтобы посмотреть статистику и попытки студентов."
      />

      <div className="ui-toolbar">
        <select value={selectedTestId} onChange={(event) => setSelectedTestId(event.target.value)}>
          <option value="">Выберите тест</option>
          {tests.map((test) => (
            <option key={test.id} value={test.id}>
              {test.title}
            </option>
          ))}
        </select>
      </div>

      {error ? <div className="ui-error">{error}</div> : null}
      {success ? <div className="ui-success">{success}</div> : null}
      {loading ? <div className="ui-info">Загрузка результатов...</div> : null}

      {!loading && tests.length === 0 ? (
        <EmptyState title="У вас пока нет тестов" description="Создайте тест, чтобы здесь появилась статистика." />
      ) : null}

      {!loading && selectedTestId ? (
        <>
          <div className="ui-stats">
            {cards.map((card) => (
              <article key={card.label} className="ui-stat-card">
                <span>{card.label}</span>
                <strong>{card.value}</strong>
              </article>
            ))}
          </div>

          {attempts.length === 0 ? (
            <EmptyState title="Попыток пока нет" description="Студенты ещё не начали выбранный тест." />
          ) : (
            <div className="ui-table-card">
              <table className="ui-table">
                <thead>
                  <tr>
                    <th>Студент</th>
                    <th>Попытка</th>
                    <th>Балл</th>
                    <th>Просрочено</th>
                    <th>Требует проверки</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {attempts.map((attempt) => (
                    <tr key={attempt.id}>
                      <td>{attempt.student_name}</td>
                      <td>{attempt.attempt_number}</td>
                      <td>
                        {attempt.total_score}/{attempt.max_score}
                      </td>
                      <td>{attempt.is_overdue ? "Просрочено" : "—"}</td>
                      <td>{attempt.essay_review_pending ? "Требует проверки" : "—"}</td>
                      <td>
                        <button
                          type="button"
                          className="button button-secondary"
                          onClick={() => {
                            setSuccess("");
                            setSelectedAttempt(attempt);
                          }}
                        >
                          Открыть результаты
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      ) : null}

      <Modal
        isOpen={Boolean(selectedAttempt)}
        title={selectedAttempt ? `Результаты: ${selectedAttempt.student_name}` : "Результаты"}
        onClose={() => setSelectedAttempt(null)}
        actions={
          <button type="button" className="button button-secondary" onClick={() => setSelectedAttempt(null)}>
            Закрыть
          </button>
        }
      >
        {success ? <div className="ui-success">Результаты сохранены.</div> : null}
        <div className={styles.answersList}>
          {(selectedAttempt?.answers ?? []).map((answer) => (
            <article key={answer.id} className={styles.answerCard}>
              <div className={styles.answerHeader}>
                <div>
                  <h4>{answer.question_title}</h4>
                  <p>{answer.question_prompt}</p>
                </div>
                <span
                  className={
                    answer.question_type === "extended" && answer.reviewed_at
                      ? "ui-status-success"
                      : answer.is_correct === false
                        ? "ui-status-danger"
                        : answer.is_correct === null
                          ? "ui-status-neutral"
                          : "ui-status-success"
                  }
                >
                  {answer.question_type === "extended"
                    ? answer.reviewed_at
                      ? "Проверено"
                      : "На проверке"
                    : answer.is_correct
                      ? "Верно"
                      : "Неверно"}
                </span>
              </div>

              <div className={styles.answerMeta}>
                <p><strong>Ответ студента:</strong> {formatAnswer(answer)}</p>
                <p><strong>Правильный ответ:</strong> {formatCorrectAnswer(answer)}</p>
                <p><strong>Баллы:</strong> {answer.earned_points}/{answer.max_points}</p>
              </div>

              {answer.question_type === "extended" ? (
                <div className={styles.essayReview}>
                  <input
                    type="number"
                    min={0}
                    max={Number(answer.max_points)}
                    placeholder="Баллы"
                    value={essayScores[answer.id] ?? answer.manual_points ?? ""}
                    onChange={(event) =>
                      setEssayScores((previous) => ({ ...previous, [answer.id]: event.target.value }))
                    }
                  />
                  <textarea
                    rows={4}
                    placeholder="Комментарий"
                    value={essayComments[answer.id] ?? answer.teacher_comment ?? ""}
                    onChange={(event) =>
                      setEssayComments((previous) => ({ ...previous, [answer.id]: event.target.value }))
                    }
                  />
                  <button type="button" className="button button-primary" onClick={() => void saveEssay(answer.id)}>
                    Сохранить
                  </button>
                </div>
              ) : null}
            </article>
          ))}
        </div>
      </Modal>
    </div>
  );
}
