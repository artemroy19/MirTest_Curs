import { useEffect, useMemo, useState } from "react";

import { apiClient } from "../../api/client";
import { SectionHeader } from "../../components/layout/SectionHeader/SectionHeader";
import { ConfirmModal } from "../../components/common/ConfirmModal/ConfirmModal";
import { EmptyState } from "../../components/common/EmptyState/EmptyState";
import { Modal } from "../../components/common/Modal/Modal";
import { QuestionCard } from "../../components/question-bank/QuestionCard/QuestionCard";
import { QuestionFormModal } from "../../components/question-bank/QuestionFormModal/QuestionFormModal";
import { QuestionType } from "../../types/domain";
import { extractList } from "../../utils/extractList";
import { getQuestionTypeLabel } from "../../constants/questionTypes";
import styles from "./QuestionBankPage.module.css";

type Category = {
  id: number;
  title: string;
};

type Question = {
  id: number;
  title: string;
  prompt: string;
  question_type: QuestionType;
  base_points: number | string;
  payload: any;
  category?: Category | null;
};

type QuestionSavePayload = Omit<Question, "base_points" | "category" | "id"> & {
  id?: number;
  base_points: string;
  category: number | null;
};

const questionTypes: Array<{ value: QuestionType; label: string }> = [
  { value: "single", label: getQuestionTypeLabel("single") },
  { value: "multiple", label: getQuestionTypeLabel("multiple") },
  { value: "text", label: getQuestionTypeLabel("text") },
  { value: "extended", label: getQuestionTypeLabel("extended") },
];

function renderQuestionPreview(question: Question) {
  const payload = typeof question.payload === "string" ? JSON.parse(question.payload) : question.payload || {};

  if (question.question_type === "single") {
    return (
      <div className={styles.optionList}>
        {(payload.options || []).map((option: any) => (
          <div key={option.id} className={styles.optionItem}>
            <span>{option.text}</span>
            {payload.correct_option === option.id ? <span className={styles.badge}>Правильный</span> : null}
          </div>
        ))}
      </div>
    );
  }

  if (question.question_type === "multiple") {
    const correctSet = new Set(payload.correct_options || []);
    return (
      <div className={styles.optionList}>
        {(payload.options || []).map((option: any) => (
          <div key={option.id} className={styles.optionItem}>
            <span>{option.text}</span>
            {correctSet.has(option.id) ? <span className={styles.badge}>Правильный</span> : null}
          </div>
        ))}
      </div>
    );
  }

  if (question.question_type === "text") {
    return (
      <div className={styles.optionList}>
        {(payload.correct_answers || []).map((answer: string, index: number) => (
          <div key={index} className={styles.optionItem}>
            <span>{answer}</span>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className={styles.optionList}>
      <div className={styles.optionItem}>Развёрнутый вопрос. Студенту доступно текстовое поле.</div>
    </div>
  );
}

export function QuestionBankPage() {
  const [questions, setQuestions] = useState<Question[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [typeFilter, setTypeFilter] = useState<QuestionType | "">("");
  const [categoryFilter, setCategoryFilter] = useState<number | "">("");
  const [previewQuestion, setPreviewQuestion] = useState<Question | null>(null);
  const [editingQuestion, setEditingQuestion] = useState<QuestionSavePayload | null>(null);
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [isCategoryModalOpen, setIsCategoryModalOpen] = useState(false);
  const [newCategoryTitle, setNewCategoryTitle] = useState("");
  const [newCategoryDescription, setNewCategoryDescription] = useState("");
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [questionToDelete, setQuestionToDelete] = useState<number | null>(null);
  const [error, setError] = useState("");

  async function loadData() {
    try {
      setError("");
      const [questionsRes, categoriesRes] = await Promise.all([
        apiClient.get("/questions/", { params: { is_bank_question: true } }),
        apiClient.get("/categories/"),
      ]);
      setQuestions(extractList(questionsRes.data));
      setCategories(extractList(categoriesRes.data));
    } catch {
      setError("Не удалось загрузить вопросы или категории.");
    }
  }

  useEffect(() => {
    void loadData();
  }, []);

  const filteredQuestions = useMemo(() => {
    return questions.filter((question) => {
      const matchesSearch = question.title.toLowerCase().includes(searchTerm.toLowerCase()) || question.prompt.toLowerCase().includes(searchTerm.toLowerCase());
      const matchesType = typeFilter ? question.question_type === typeFilter : true;
      const matchesCategory = categoryFilter ? question.category?.id === categoryFilter : true;
      return matchesSearch && matchesType && matchesCategory;
    });
  }, [questions, searchTerm, typeFilter, categoryFilter]);

  async function handleDelete(questionId: number) {
    setQuestionToDelete(questionId);
    setDeleteConfirmOpen(true);
  }

  async function handleDeleteConfirm() {
    if (!questionToDelete) return;

    try {
      await apiClient.delete(`/questions/${questionToDelete}/`);
      setQuestionToDelete(null);
      setDeleteConfirmOpen(false);
      await loadData();
    } catch {
      setError("Не удалось удалить вопрос.");
    }
  }

  async function handleSave(question: QuestionSavePayload) {
    try {
      if (question.id) {
        await apiClient.patch(`/questions/${question.id}/`, {
          title: question.title,
          prompt: question.prompt,
          question_type: question.question_type,
          base_points: question.base_points,
          payload: question.payload,
          category_id: question.category,
          is_bank_question: true,
        });
      } else {
        await apiClient.post(`/questions/`, {
          title: question.title,
          prompt: question.prompt,
          question_type: question.question_type,
          base_points: question.base_points,
          payload: question.payload,
          category_id: question.category,
          is_bank_question: true,
        });
      }
      setIsFormOpen(false);
      setEditingQuestion(null);
      await loadData();
    } catch {
      setError("Не удалось сохранить вопрос.");
    }
  }

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <div className={styles.questionsArea}>
          <h1 className={styles.title}>Банк вопросов</h1>
          <p>Управляйте вопросами, фильтруйте по типу и быстро создавайте новые задачи.</p>
        </div>
        <div className={styles.headerActions}>
          <button type="button" className={styles.secondaryButton} onClick={() => setIsCategoryModalOpen(true)}>
            Создать категорию
          </button>
          <button type="button" className={styles.createButton} onClick={() => setIsFormOpen(true)}>
            Создать вопрос
          </button>
        </div>
      </div>

      <div className={styles.panel}>
        <aside className={styles.sidebar}>
          <h3>Категории</h3>
          <button
            type="button"
            className={`${styles.categoryButton} ${categoryFilter === "" ? styles.active : ""}`}
            onClick={() => setCategoryFilter("")}
          >
            Все категории
          </button>
          {categories.map((category) => (
            <button
              key={category.id}
              type="button"
              className={`${styles.categoryButton} ${categoryFilter === category.id ? styles.active : ""}`}
              onClick={() => setCategoryFilter(category.id)}
            >
              {category.title}
            </button>
          ))}
        </aside>

        <div>
          <div className={styles.filters}>
            <input
              type="text"
              className={styles.searchInput}
              placeholder="Поиск по тексту или заголовку..."
              value={searchTerm}
              onChange={(event) => setSearchTerm(event.target.value)}
            />
            <select
              className={styles.selectInput}
              value={typeFilter}
              onChange={(event) => setTypeFilter(event.target.value as QuestionType | "")}
            >
              <option value="">Все типы</option>
              {questionTypes.map((item) => (
                <option key={item.value} value={item.value}>
                  {item.label}
                </option>
              ))}
            </select>
          </div>

          {error && <p className={styles.noItems}>{error}</p>}

          {questions.length === 0 ? (
            <EmptyState
              title="В банке вопросов пока пусто"
              description="Создайте первый вопрос, чтобы собирать из них тесты."
              actionLabel="Создать первый вопрос"
              onAction={() => setIsFormOpen(true)}
            />
          ) : filteredQuestions.length === 0 ? (
            <EmptyState title="Ничего не найдено" description="Попробуйте изменить параметры поиска." />
          ) : (
            <div className={styles.questionList}>
              {filteredQuestions.map((question) => (
                <QuestionCard
                  key={question.id}
                  question={question}
                  onPreview={(q) => setPreviewQuestion(q)}
                  onEdit={(q) => {
                    setEditingQuestion({ ...q, category: q.category?.id ?? null, base_points: String(q.base_points) });
                    setIsFormOpen(true);
                  }}
                  onDelete={(q) => handleDelete(q.id)}
                />
              ))}
            </div>
          )}
        </div>
      </div>

      <QuestionFormModal
        isOpen={isFormOpen}
        categories={categories}
        question={editingQuestion}
        onClose={() => {
          setIsFormOpen(false);
          setEditingQuestion(null);
        }}
        onSave={handleSave}
      />

      <Modal
        isOpen={isCategoryModalOpen}
        title="Создать категорию"
        onClose={() => setIsCategoryModalOpen(false)}
        actions={
          <>
            <button type="button" className="button button-secondary" onClick={() => setIsCategoryModalOpen(false)}>
              Отмена
            </button>
            <button type="button" className="button button-primary" onClick={async () => {
              if (!newCategoryTitle.trim()) return;
              try {
                await apiClient.post("/categories/", {
                  title: newCategoryTitle,
                  description: newCategoryDescription,
                });
                setNewCategoryTitle("");
                setNewCategoryDescription("");
                setIsCategoryModalOpen(false);
                await loadData();
              } catch {
                setError("Не удалось создать категорию.");
              }
            }}>
              Создать
            </button>
          </>
        }
      >
        <div className={styles.categoryForm}>
          <label>
            Название категории
            <input
              type="text"
              placeholder="Название категории"
              value={newCategoryTitle}
              onChange={(event) => setNewCategoryTitle(event.target.value)}
            />
          </label>
          <label>
            Описание (необязательно)
            <textarea
              placeholder="Описание (необязательно)"
              value={newCategoryDescription}
              onChange={(event) => setNewCategoryDescription(event.target.value)}
              rows={3}
            />
          </label>
        </div>
      </Modal>

      <ConfirmModal
        isOpen={deleteConfirmOpen}
        title="Удалить вопрос?"
        description="Это действие нельзя отменить."
        onConfirm={handleDeleteConfirm}
        onCancel={() => setDeleteConfirmOpen(false)}
        danger
      />

      <Modal
        isOpen={Boolean(previewQuestion)}
        title={previewQuestion?.title || "Предпросмотр вопроса"}
        onClose={() => setPreviewQuestion(null)}
        description={previewQuestion ? getQuestionTypeLabel(previewQuestion.question_type) : undefined}
      >
        {previewQuestion ? (
          <div className={styles.previewBlock}>
            <p className={styles.previewLabel}>Текст вопроса</p>
            <p className={styles.previewText}>{previewQuestion.prompt}</p>
            <div className={styles.previewBlock}>
              <span className={styles.badge}>{getQuestionTypeLabel(previewQuestion.question_type)}</span>
              <span className={styles.previewLabel}>Баллы: {previewQuestion.base_points}</span>
            </div>
            {renderQuestionPreview(previewQuestion)}
          </div>
        ) : null}
      </Modal>
    </div>
  );
}
