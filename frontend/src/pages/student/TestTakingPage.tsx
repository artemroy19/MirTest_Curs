import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { apiClient } from "../../api/client";
import { ConfirmModal } from "../../components/common/ConfirmModal/ConfirmModal";
import { SectionHeader } from "../../components/layout/SectionHeader/SectionHeader";
import styles from "./TestTakingPage.module.css";

type AnswerItem = {
  id: number;
  test_question: number;
  question_title: string;
  question_type: "single" | "multiple" | "text" | "extended";
  question_prompt: string;
  question_payload: {
    options?: Array<{ id: string | number; text?: string; label?: string }>;
  };
  order: number;
  answer_payload: Record<string, unknown>;
};

type Attempt = {
  id: number;
  status: "in_progress" | "completed";
  started_at: string;
  test_title: string;
  timer_minutes: number | null;
  answers: AnswerItem[];
};

function hasAnswer(answer: Record<string, unknown>) {
  if (!answer) {
    return false;
  }
  if (Array.isArray(answer.selected)) {
    return answer.selected.length > 0;
  }
  if (typeof answer.selected === "string" || typeof answer.selected === "number") {
    return true;
  }
  if (typeof answer.value === "string") {
    return answer.value.trim().length > 0;
  }
  return Object.keys(answer).length > 0;
}

function formatTimer(value: number) {
  const hours = String(Math.floor(value / 3600)).padStart(2, "0");
  const minutes = String(Math.floor((value % 3600) / 60)).padStart(2, "0");
  const seconds = String(value % 60).padStart(2, "0");
  return `${hours}:${minutes}:${seconds}`;
}

export function TestTakingPage() {
  const { attemptId } = useParams();
  const navigate = useNavigate();
  const [attempt, setAttempt] = useState<Attempt | null>(null);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [drafts, setDrafts] = useState<Record<number, Record<string, unknown>>>({});
  const [remainingSeconds, setRemainingSeconds] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [submitOpen, setSubmitOpen] = useState(false);
  const [error, setError] = useState("");

  const answers = useMemo(
    () => (attempt?.answers ?? []).slice().sort((left, right) => left.order - right.order),
    [attempt],
  );
  const current = answers[currentIndex] ?? null;

  useEffect(() => {
    async function loadAttempt() {
      if (!attemptId) {
        return;
      }
      setLoading(true);
      setError("");
      try {
        const response = await apiClient.get(`/attempts/${attemptId}/`);
        setAttempt(response.data);
      } catch {
        setError("Не удалось загрузить попытку.");
      } finally {
        setLoading(false);
      }
    }

    void loadAttempt();
  }, [attemptId]);

  useEffect(() => {
    if (!attempt?.timer_minutes) {
      setRemainingSeconds(null);
      return;
    }

    const startTime = new Date(attempt.started_at).getTime();
    const finishTime = startTime + attempt.timer_minutes * 60_000;

    const updateRemaining = () => {
      const seconds = Math.max(0, Math.floor((finishTime - Date.now()) / 1000));
      setRemainingSeconds(seconds);
    };

    updateRemaining();
    const timerId = window.setInterval(updateRemaining, 1000);
    return () => window.clearInterval(timerId);
  }, [attempt]);

  useEffect(() => {
    if (attempt?.status === "in_progress" && remainingSeconds === 0) {
      void handleSubmit(true);
    }
  }, [attempt, remainingSeconds]);

  async function persistCurrentAnswer() {
    if (!attempt || !current) {
      return;
    }
    const answerPayload = drafts[current.id] ?? current.answer_payload ?? {};
    await apiClient.post(`/attempts/${attempt.id}/save-answer/`, {
      test_question: current.test_question,
      answer_payload: answerPayload,
    });
    setAttempt((previous) =>
      previous
        ? {
            ...previous,
            answers: previous.answers.map((answer) =>
              answer.id === current.id ? { ...answer, answer_payload: answerPayload } : answer,
            ),
          }
        : previous,
    );
  }

  async function goToQuestion(nextIndex: number) {
    try {
      setSaving(true);
      setError("");
      await persistCurrentAnswer();
      setCurrentIndex(nextIndex);
    } catch {
      setError("Не удалось сохранить ответ.");
    } finally {
      setSaving(false);
    }
  }

  async function handleSubmit(isAutomatic = false) {
    if (!attempt) {
      return;
    }
    try {
      setSaving(true);
      setError("");
      await persistCurrentAnswer();
      await apiClient.post(`/attempts/${attempt.id}/submit/`);
      navigate("/results", {
        state: {
          message: isAutomatic ? "Время вышло, попытка завершена автоматически." : undefined,
        },
      });
    } catch {
      setError("Не удалось завершить тест.");
    } finally {
      setSaving(false);
      setSubmitOpen(false);
    }
  }

  function updateCurrentAnswer(payload: Record<string, unknown>) {
    if (!current) {
      return;
    }
    setDrafts((previous) => ({ ...previous, [current.id]: payload }));
  }

  function renderQuestionField() {
    if (!current) {
      return null;
    }
    const payload = current.question_payload ?? {};
    const answer = drafts[current.id] ?? current.answer_payload ?? {};

    if (current.question_type === "single") {
      return (
        <div className={styles.choiceList}>
          {(payload.options ?? []).map((option) => (
            <label key={String(option.id)} className={styles.choiceItem}>
              <input
                type="radio"
                name={`question-${current.id}`}
                checked={answer.selected === option.id}
                onChange={() => updateCurrentAnswer({ selected: option.id })}
              />
              <span className={styles.choiceText}>{option.text || option.label || `Вариант ${option.id}`}</span>
            </label>
          ))}
        </div>
      );
    }

    if (current.question_type === "multiple") {
      const selected = new Set(Array.isArray(answer.selected) ? answer.selected : []);
      return (
        <div className={styles.choiceList}>
          {(payload.options ?? []).map((option) => (
            <label key={String(option.id)} className={styles.choiceItem}>
              <input
                type="checkbox"
                checked={selected.has(option.id)}
                onChange={() => {
                  const next = new Set(selected);
                  if (next.has(option.id)) {
                    next.delete(option.id);
                  } else {
                    next.add(option.id);
                  }
                  updateCurrentAnswer({ selected: Array.from(next) });
                }}
              />
              <span className={styles.choiceText}>{option.text || option.label || `Вариант ${option.id}`}</span>
            </label>
          ))}
        </div>
      );
    }

    if (current.question_type === "extended") {
      return (
        <textarea
          className={styles.textarea}
          rows={8}
          value={String(answer.value ?? "")}
          onChange={(event) => updateCurrentAnswer({ value: event.target.value })}
          placeholder="Введите развернутый ответ"
        />
      );
    }

    return (
      <input
        className={styles.textInput}
        value={String(answer.value ?? "")}
        onChange={(event) => updateCurrentAnswer({ value: event.target.value })}
        placeholder="Введите краткий ответ"
      />
    );
  }

  return (
    <div className={styles.page}>
      <SectionHeader
        eyebrow="Прохождение теста"
        title={attempt?.test_title || "Загрузка теста"}
        description="Отвечайте на вопросы последовательно или переходите по номерам справа."
      />

      {error ? <div className={styles.error}>{error}</div> : null}
      {loading ? <div className="ui-info">Загрузка попытки...</div> : null}
      {!loading && saving ? <div className="ui-info">Сохраняем ответ...</div> : null}

      {attempt ? (
        <>
          <section className={styles.headerCard}>
            <div>
              <span className={styles.caption}>
                Вопрос {currentIndex + 1} из {answers.length}
              </span>
              <h2>{current?.question_title}</h2>
            </div>
            {remainingSeconds !== null ? (
              <div className={`${styles.timer} ${remainingSeconds <= 300 ? styles.timerDanger : ""}`}>
                {formatTimer(remainingSeconds)}
              </div>
            ) : null}
          </section>

          <div className={styles.layout}>
            <aside className={styles.questionMap}>
              {answers.map((answer, index) => {
                const payload = drafts[answer.id] ?? answer.answer_payload ?? {};
                const statusClass =
                  index === currentIndex
                    ? styles.currentQuestion
                    : hasAnswer(payload)
                      ? styles.answeredQuestion
                      : styles.unansweredQuestion;

                return (
                  <button
                    key={answer.id}
                    type="button"
                    className={`${styles.questionIndex} ${statusClass}`}
                    onClick={() => {
                      if (index !== currentIndex) {
                        void goToQuestion(index);
                      }
                    }}
                  >
                    {index + 1}
                  </button>
                );
              })}
            </aside>

            <section className={styles.contentCard}>
              <div className={styles.questionBody}>
                <h3 className={styles.questionTitle}>{current?.question_title || "Вопрос"}</h3>
                <p className={styles.prompt}>{current?.question_prompt || current?.question_title}</p>
              </div>
              {renderQuestionField()}

              <div className={styles.actions}>
                <button
                  type="button"
                  className="button button-secondary"
                  disabled={currentIndex === 0 || saving}
                  onClick={() => void goToQuestion(currentIndex - 1)}
                >
                  Назад
                </button>

                {currentIndex < answers.length - 1 ? (
                  <button
                    type="button"
                    className="button button-secondary"
                    disabled={saving}
                    onClick={() => void goToQuestion(currentIndex + 1)}
                  >
                    Вперёд
                  </button>
                ) : (
                  <button
                    type="button"
                    className="button button-primary"
                    disabled={saving}
                    onClick={() => setSubmitOpen(true)}
                  >
                    Завершить
                  </button>
                )}
              </div>
            </section>
          </div>
        </>
      ) : null}

      <ConfirmModal
        isOpen={submitOpen}
        title="Завершить тест?"
        description="После завершения изменить ответы уже не получится."
        confirmLabel="Завершить"
        cancelLabel="Продолжить тест"
        onCancel={() => setSubmitOpen(false)}
        onConfirm={() => void handleSubmit(false)}
      />
    </div>
  );
}
