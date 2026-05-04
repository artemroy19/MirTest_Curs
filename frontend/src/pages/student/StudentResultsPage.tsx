import { useEffect, useMemo, useState } from "react";

import { apiClient } from "../../api/client";
import { EmptyState } from "../../components/common/EmptyState/EmptyState";
import { Modal } from "../../components/common/Modal/Modal";
import { SectionHeader } from "../../components/layout/SectionHeader/SectionHeader";
import { extractList } from "../../utils/extractList";
import styles from "./StudentResultsPage.module.css";

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
  teacher_comment: string;
  reviewed_at: string | null;
};

type Attempt = {
  id: number;
  test: number;
  test_title: string;
  result_visibility: "score_only" | "score_with_review";
  attempt_number: number;
  total_score: string;
  max_score: string;
  is_overdue: boolean;
  essay_review_pending: boolean;
  answers: AttemptAnswer[];
};

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
  return "—";
}

export function ResultsPage() {
  const [attempts, setAttempts] = useState<Attempt[]>([]);
  const [selectedTest, setSelectedTest] = useState("");
  const [selectedAttempt, setSelectedAttempt] = useState<Attempt | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadAttempts() {
      setLoading(true);
      setError("");
      try {
        const response = await apiClient.get("/attempts/");
        setAttempts(extractList(response.data));
      } catch {
        setError("Не удалось загрузить результаты.");
      } finally {
        setLoading(false);
      }
    }

    void loadAttempts();
  }, []);

  const tests = useMemo(() => {
    const seen = new Map<number, string>();
    attempts.forEach((attempt) => {
      seen.set(attempt.test, attempt.test_title);
    });
    return Array.from(seen.entries()).map(([id, title]) => ({ id, title }));
  }, [attempts]);

  const filteredAttempts = useMemo(() => {
    if (!selectedTest) {
      return attempts;
    }
    return attempts.filter((attempt) => String(attempt.test) === selectedTest);
  }, [attempts, selectedTest]);

  return (
    <div className="ui-page">
      <SectionHeader
        title="Результаты"
        description="Выберите тест и просмотрите историю своих попыток."
      />

      <div className="ui-toolbar">
        <select value={selectedTest} onChange={(event) => setSelectedTest(event.target.value)}>
          <option value="">Все тесты</option>
          {tests.map((test) => (
            <option key={test.id} value={test.id}>
              {test.title}
            </option>
          ))}
        </select>
      </div>

      {error ? <div className="ui-error">{error}</div> : null}
      {loading ? <div className="ui-info">Загрузка результатов...</div> : null}

      {!loading && attempts.length === 0 ? (
        <EmptyState title="Результатов пока нет" description="После прохождения тестов здесь появятся ваши попытки." />
      ) : null}

      {!loading && attempts.length > 0 && filteredAttempts.length === 0 ? (
        <EmptyState title="Ничего не найдено" description="Попробуйте изменить параметры поиска." />
      ) : null}

      {!loading && filteredAttempts.length > 0 ? (
        <div className={styles.resultsGrid}>
          {filteredAttempts.map((attempt) => (
            <article key={attempt.id} className={styles.resultCard}>
              <div className={styles.resultMain}>
                <div>
                  <h3>{attempt.test_title}</h3>
                  <p>Попытка {attempt.attempt_number}</p>
                </div>
                <span className={attempt.is_overdue ? "ui-status-danger" : "ui-status-success"}>
                  {attempt.is_overdue ? "Просрочено" : "Сдано"}
                </span>
              </div>

              <div className={styles.scorePanel}>
                <span>{attempt.essay_review_pending ? "Ожидает проверки" : "Итоговый балл"}</span>
                <strong>{attempt.essay_review_pending ? "На проверке" : `${attempt.total_score}/${attempt.max_score}`}</strong>
              </div>

              <button
                type="button"
                className={`button ${attempt.essay_review_pending ? styles.pendingResultButton : "button-secondary"}`}
                disabled={attempt.essay_review_pending}
                onClick={() => setSelectedAttempt(attempt)}
              >
                Открыть результаты
              </button>
            </article>
          ))}
        </div>
      ) : null}

      <Modal
        isOpen={Boolean(selectedAttempt)}
        title={selectedAttempt?.test_title || "Результаты попытки"}
        onClose={() => setSelectedAttempt(null)}
        actions={
          <button type="button" className="button button-secondary" onClick={() => setSelectedAttempt(null)}>
            Закрыть
          </button>
        }
      >
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
                    answer.question_type === "extended"
                      ? answer.reviewed_at
                        ? "ui-status-success"
                        : "ui-status-neutral"
                      : answer.is_correct === false
                        ? "ui-status-danger"
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
                <p><strong>Ваш ответ:</strong> {formatAnswer(answer)}</p>
                {selectedAttempt?.result_visibility === "score_with_review" ? (
                  <p><strong>Правильный ответ:</strong> {formatCorrectAnswer(answer)}</p>
                ) : null}
                <p><strong>Баллы:</strong> {answer.earned_points}/{answer.max_points}</p>
                {answer.teacher_comment ? <p><strong>Комментарий преподавателя:</strong> {answer.teacher_comment}</p> : null}
              </div>
            </article>
          ))}
        </div>
      </Modal>
    </div>
  );
}
