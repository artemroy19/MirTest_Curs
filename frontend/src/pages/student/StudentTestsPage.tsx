import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { apiClient } from "../../api/client";
import { ConfirmModal } from "../../components/common/ConfirmModal/ConfirmModal";
import { EmptyState } from "../../components/common/EmptyState/EmptyState";
import { SectionHeader } from "../../components/layout/SectionHeader/SectionHeader";
import { extractList } from "../../utils/extractList";
import styles from "./StudentTestsPage.module.css";

type TestCard = {
  id: number;
  title: string;
  description: string;
  questions_count: number;
  deadline: string | null;
  timer_minutes: number | null;
  max_score: string;
  availability: {
    code: "available" | "attempts_exhausted" | "deadline_passed";
    label: string;
    can_start: boolean;
    attempts_used: number;
    attempts_limit: number | null;
  } | null;
};

function formatDeadline(value: string | null) {
  if (!value) {
    return "Без дедлайна";
  }
  return new Date(value).toLocaleString("ru-RU");
}

export function StudentTestsPage() {
  const navigate = useNavigate();
  const [tests, setTests] = useState<TestCard[]>([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [testToStart, setTestToStart] = useState<TestCard | null>(null);

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError("");
      try {
        const response = await apiClient.get("/tests/available/");
        setTests(extractList(response.data));
      } catch {
        setError("Не удалось загрузить список тестов.");
      } finally {
        setLoading(false);
      }
    }

    void load();
  }, []);

  const filteredTests = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) {
      return tests;
    }
    return tests.filter(
      (test) =>
        test.title.toLowerCase().includes(normalized) ||
        test.description.toLowerCase().includes(normalized),
    );
  }, [query, tests]);

  async function handleStart(testId: number) {
    try {
      const response = await apiClient.post("/attempts/start/", { test: testId });
      navigate(`/test/${testId}/attempt/${response.data.id}`);
    } catch {
      setError("Не удалось начать тест.");
    }
  }

  return (
    <div className="ui-page">
      <SectionHeader
        title="Мои тесты"
        description="Здесь собраны все тесты, назначенные вам преподавателями."
      />

      <div className="ui-toolbar">
        <input
          className={styles.search}
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Поиск по названию или описанию"
        />
      </div>

      {error ? <div className="ui-error">{error}</div> : null}
      {loading ? <div className="ui-info">Загрузка тестов...</div> : null}

      {!loading && tests.length === 0 ? (
        <EmptyState title="Тестов пока нет" description="Когда преподаватель назначит вам тесты, они появятся на этой странице." />
      ) : null}

      {!loading && tests.length > 0 && filteredTests.length === 0 ? (
        <EmptyState
          title="Ничего не найдено"
          description="Попробуйте изменить параметры поиска."
        />
      ) : null}

      {!loading && filteredTests.length > 0 ? (
        <div className="ui-grid-cards">
          {filteredTests.map((test) => {
            const availability = test.availability;
            const availabilityCode = availability?.code ?? "available";

            return (
              <article key={test.id} className={`${styles.card} ui-card`}>
                <div className="ui-card-header">
                  <div>
                    <h3>{test.title}</h3>
                    <p>{test.description || "Описание не указано."}</p>
                  </div>
                  <span className="ui-badge">{test.questions_count} вопросов</span>
                </div>

                <dl className="ui-meta">
                  <div>
                    <dt>Максимум</dt>
                    <dd>{test.max_score}</dd>
                  </div>
                  <div>
                    <dt>Таймер</dt>
                    <dd>{test.timer_minutes ? `${test.timer_minutes} мин` : "Без таймера"}</dd>
                  </div>
                  <div>
                    <dt>Дедлайн</dt>
                    <dd>{formatDeadline(test.deadline)}</dd>
                  </div>
                  <div>
                    <dt>Попытки</dt>
                    <dd>
                      {availability?.attempts_limit == null
                        ? `${availability?.attempts_used ?? 0} / без лимита`
                        : `${availability?.attempts_used ?? 0} / ${availability.attempts_limit}`}
                    </dd>
                  </div>
                </dl>

                <button
                  type="button"
                  className={`${styles.actionButton} ${styles[availabilityCode]}`}
                  disabled={!availability?.can_start}
                  onClick={() => setTestToStart(test)}
                >
                  {availability?.label ?? "Пройти"}
                </button>
              </article>
            );
          })}
        </div>
      ) : null}

      <ConfirmModal
        isOpen={Boolean(testToStart)}
        title="Начать тест?"
        description={testToStart ? `Вы действительно хотите приступить к тесту "${testToStart.title}"?` : ""}
        confirmLabel="Да, начать"
        cancelLabel="Нет"
        onCancel={() => setTestToStart(null)}
        onConfirm={() => {
          const testId = testToStart?.id;
          setTestToStart(null);
          if (testId) {
            void handleStart(testId);
          }
        }}
      />
    </div>
  );
}
