import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { DndContext, PointerSensor, useSensor, useSensors } from "@dnd-kit/core";
import { SortableContext, arrayMove, rectSortingStrategy, useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";

import { apiClient } from "../../api/client";
import { EmptyState } from "../../components/common/EmptyState/EmptyState";
import { Modal } from "../../components/common/Modal/Modal";
import { SectionHeader } from "../../components/layout/SectionHeader/SectionHeader";
import { getQuestionTypeLabel } from "../../constants/questionTypes";
import { QuestionType } from "../../types/domain";
import { extractList } from "../../utils/extractList";
import styles from "./TeacherTestConstructorPage.module.css";

type Category = {
  id: number;
  title: string;
};

type BankQuestion = {
  id: number;
  title: string;
  question_type: QuestionType;
  category?: Category | null;
  base_points: number;
};

type ConstructorQuestion = {
  id: number;
  title: string;
  question_type: QuestionType;
  category?: Category | null;
  base_points: number;
  testQuestionId?: number;
};

type TestInfo = {
  title: string;
  description: string;
  timer_minutes: number | null;
  attempts_limit: number | null;
  deadline: string;
  result_visibility: "score_only" | "score_with_review";
  questions: ConstructorQuestion[];
};

function SortableQuestion({ question, onRemove }: { question: ConstructorQuestion; onRemove: (id: number) => void }) {
  const { attributes, listeners, setNodeRef, transform, transition } = useSortable({ id: question.id });
  return (
    <div
      ref={setNodeRef}
      style={{ transform: CSS.Transform.toString(transform), transition }}
      className={styles.questionCard}
    >
      <button type="button" className={styles.dragHandle} {...attributes} {...listeners}>
        ::
      </button>
      <div className={styles.questionInfo}>
        <strong>{question.title}</strong>
        <span>{getQuestionTypeLabel(question.question_type)}</span>
      </div>
      <button type="button" className={styles.removeButton} onClick={() => onRemove(question.id)}>
        Убрать
      </button>
    </div>
  );
}

export function TeacherTestConstructorPage() {
  const { testId } = useParams();
  const navigate = useNavigate();
  const sensors = useSensors(useSensor(PointerSensor));
  const [test, setTest] = useState<TestInfo>({
    title: "",
    description: "",
    timer_minutes: null,
    attempts_limit: null,
    deadline: "",
    result_visibility: "score_with_review",
    questions: [],
  });
  const [initialQuestions, setInitialQuestions] = useState<ConstructorQuestion[]>([]);
  const [bankQuestions, setBankQuestions] = useState<BankQuestion[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [bankFilter, setBankFilter] = useState<string>("");
  const [bankOpen, setBankOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError("");
      try {
        const [questionsRes, categoriesRes] = await Promise.all([
          apiClient.get("/questions/", { params: { is_bank_question: true } }),
          apiClient.get("/categories/"),
        ]);

        setBankQuestions(extractList(questionsRes.data));
        setCategories(extractList(categoriesRes.data));

        if (testId) {
          const response = await apiClient.get(`/tests/${testId}/`);
          const loadedQuestions = (response.data.test_questions ?? []).map((item: any) => ({
            id: item.question_data.id,
            title: item.question_data.title,
            question_type: item.question_data.question_type,
            category: item.question_data.category,
            base_points: Number(item.overridden_points ?? item.question_data.base_points ?? 0),
            testQuestionId: item.id,
          }));

          setInitialQuestions(loadedQuestions);
          setTest({
            title: response.data.title,
            description: response.data.description ?? "",
            timer_minutes: response.data.timer_minutes,
            attempts_limit: response.data.attempts_limit,
            deadline: response.data.deadline ? response.data.deadline.slice(0, 16) : "",
            result_visibility: response.data.result_visibility ?? "score_with_review",
            questions: loadedQuestions,
          });
        }
      } catch {
        setError("Не удалось загрузить данные конструктора.");
      } finally {
        setLoading(false);
      }
    }

    void load();
  }, [testId]);

  const filteredBankQuestions = useMemo(() => {
    if (!bankFilter) {
      return bankQuestions;
    }
    return bankQuestions.filter((question) => String(question.category?.id ?? "") === bankFilter);
  }, [bankFilter, bankQuestions]);

  function handleDragEnd(event: any) {
    const { active, over } = event;
    if (!over || active.id === over.id) {
      return;
    }
    setTest((previous) => {
      const oldIndex = previous.questions.findIndex((question) => question.id === active.id);
      const newIndex = previous.questions.findIndex((question) => question.id === over.id);
      return { ...previous, questions: arrayMove(previous.questions, oldIndex, newIndex) };
    });
  }

  async function handleSave() {
    try {
      setSaving(true);
      setError("");

      const payload = {
        title: test.title,
        description: test.description,
        timer_minutes: test.timer_minutes,
        attempts_limit: test.attempts_limit,
        deadline: test.deadline || null,
        result_visibility: test.result_visibility,
      };

      let savedTestId = testId;
      if (savedTestId) {
        await apiClient.patch(`/tests/${savedTestId}/`, payload);
      } else {
        const response = await apiClient.post("/tests/", payload);
        savedTestId = String(response.data.id);
      }

      const initialByQuestionId = new Map(initialQuestions.map((question) => [question.id, question]));
      const nextQuestionIds = new Set(test.questions.map((question) => question.id));

      for (const initialQuestion of initialQuestions) {
        if (!nextQuestionIds.has(initialQuestion.id) && initialQuestion.testQuestionId) {
          await apiClient.post(`/tests/${savedTestId}/remove-question/`, { question: initialQuestion.testQuestionId });
        }
      }

      for (const question of test.questions) {
        if (!initialByQuestionId.has(question.id)) {
          await apiClient.post(`/tests/${savedTestId}/add-question/`, { question: question.id });
        }
      }

      const refreshedTest = await apiClient.get(`/tests/${savedTestId}/`);
      const reorderedIds = (refreshedTest.data.test_questions ?? [])
        .sort(
          (left: any, right: any) =>
            test.questions.findIndex((question) => question.id === left.question_data.id) -
            test.questions.findIndex((question) => question.id === right.question_data.id),
        )
        .map((item: any) => item.id);

      if (reorderedIds.length > 0) {
        await apiClient.post(`/tests/${savedTestId}/reorder-questions/`, { order: reorderedIds });
      }

      navigate("/teacher/tests");
    } catch {
      setError("Не удалось сохранить тест.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className={styles.page}>
      <SectionHeader
        title={testId ? "Редактирование теста" : "Создание теста"}
        description="Настройте параметры теста, выберите вопросы и сохраните всё одной кнопкой."
      />

      {error ? <div className={styles.error}>{error}</div> : null}
      {loading ? <div className={styles.info}>Загрузка конструктора...</div> : null}

      {!loading ? (
        <div className={styles.layout}>
          <section className={styles.settingsCard}>
            <label>
              Название теста
              <input value={test.title} onChange={(event) => setTest((previous) => ({ ...previous, title: event.target.value }))} />
            </label>

            <label>
              Описание
              <textarea
                rows={4}
                value={test.description}
                onChange={(event) => setTest((previous) => ({ ...previous, description: event.target.value }))}
              />
            </label>

            <label>
              Таймер в минутах
              <input
                type="number"
                min={1}
                value={test.timer_minutes ?? ""}
                onChange={(event) =>
                  setTest((previous) => ({
                    ...previous,
                    timer_minutes: event.target.value ? Number(event.target.value) : null,
                  }))
                }
              />
            </label>

            <label>
              Лимит попыток
              <input
                type="number"
                min={1}
                value={test.attempts_limit ?? ""}
                onChange={(event) =>
                  setTest((previous) => ({
                    ...previous,
                    attempts_limit: event.target.value ? Number(event.target.value) : null,
                  }))
                }
              />
            </label>

            <label>
              Дедлайн
              <input
                type="datetime-local"
                value={test.deadline}
                onChange={(event) => setTest((previous) => ({ ...previous, deadline: event.target.value }))}
              />
            </label>

            <label>
              Видимость результатов
              <select
                value={test.result_visibility}
                onChange={(event) =>
                  setTest((previous) => ({
                    ...previous,
                    result_visibility: event.target.value as "score_only" | "score_with_review",
                  }))
                }
              >
                <option value="score_only">Только балл</option>
                <option value="score_with_review">Балл с разбором</option>
              </select>
            </label>
          </section>

          <section className={styles.questionsCard}>
            <div className={styles.questionsHeader}>
              <div>
                <h3>Вопросы теста</h3>
                <p>{test.questions.length} выбранных вопросов</p>
              </div>
              <button type="button" className="button button-secondary" onClick={() => setBankOpen(true)}>
                Выбрать из банка
              </button>
            </div>

            {test.questions.length === 0 ? (
              <EmptyState
                title="В тесте пока нет вопросов"
                description="Откройте банк вопросов и соберите структуру теста."
                actionLabel="Добавить вопросы"
                onAction={() => setBankOpen(true)}
              />
            ) : (
              <DndContext sensors={sensors} onDragEnd={handleDragEnd}>
                <SortableContext items={test.questions.map((question) => question.id)} strategy={rectSortingStrategy}>
                  <div className={styles.questionsList}>
                    {test.questions.map((question) => (
                      <SortableQuestion
                        key={question.id}
                        question={question}
                        onRemove={(questionId) =>
                          setTest((previous) => ({
                            ...previous,
                            questions: previous.questions.filter((question) => question.id !== questionId),
                          }))
                        }
                      />
                    ))}
                  </div>
                </SortableContext>
              </DndContext>
            )}
          </section>
        </div>
      ) : null}

      <div className={styles.footerActions}>
        <button type="button" className="button button-secondary" onClick={() => navigate("/teacher/tests")}>
          Отмена
        </button>
        <button
          type="button"
          className="button button-primary"
          disabled={saving || !test.title.trim()}
          onClick={() => void handleSave()}
        >
          {saving ? "Сохранение..." : "Сохранить тест"}
        </button>
      </div>

      <Modal
        isOpen={bankOpen}
        title="Банк вопросов"
        onClose={() => setBankOpen(false)}
        actions={
          <button type="button" className="button button-secondary" onClick={() => setBankOpen(false)}>
            Закрыть
          </button>
        }
      >
        <div className={styles.bankToolbar}>
          <select value={bankFilter} onChange={(event) => setBankFilter(event.target.value)}>
            <option value="">Все категории</option>
            {categories.map((category) => (
              <option key={category.id} value={category.id}>
                {category.title}
              </option>
            ))}
          </select>
        </div>

        {filteredBankQuestions.length === 0 ? (
          <EmptyState title="Ничего не найдено" description="Попробуйте изменить параметры поиска." />
        ) : (
          <div className={styles.bankList}>
            {filteredBankQuestions.map((question) => {
              const isSelected = test.questions.some((item) => item.id === question.id);
              return (
                <div key={question.id} className={styles.bankQuestion}>
                  <div>
                    <strong>{question.title}</strong>
                    <p>{getQuestionTypeLabel(question.question_type)}</p>
                  </div>
                  <button
                    type="button"
                    className={`button ${isSelected ? "button-secondary" : "button-primary"}`}
                    onClick={() =>
                      setTest((previous) => ({
                        ...previous,
                        questions: isSelected
                          ? previous.questions.filter((item) => item.id !== question.id)
                          : [
                              ...previous.questions,
                              {
                                id: question.id,
                                title: question.title,
                                question_type: question.question_type,
                                category: question.category,
                                base_points: question.base_points,
                              },
                            ],
                      }))
                    }
                  >
                    {isSelected ? "Убрать" : "Добавить"}
                  </button>
                </div>
              );
            })}
          </div>
        )}
      </Modal>
    </div>
  );
}
