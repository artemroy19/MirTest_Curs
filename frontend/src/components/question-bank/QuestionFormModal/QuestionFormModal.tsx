import { useEffect, useMemo, useState } from "react";
import { Modal } from "../../../components/common/Modal/Modal";
import { getQuestionTypeLabel } from "../../../constants/questionTypes";
import { QuestionType } from "../../../types/domain";
import styles from "./QuestionFormModal.module.css";

type Category = { id: number; title: string };

type QuestionForm = {
  id?: number;
  title: string;
  prompt: string;
  question_type: QuestionType;
  base_points: string;
  payload: any;
  category: number | null;
};

const questionTypeOptions: { value: QuestionType; label: string }[] = [
  { value: "single", label: getQuestionTypeLabel("single") },
  { value: "multiple", label: getQuestionTypeLabel("multiple") },
  { value: "text", label: getQuestionTypeLabel("text") },
  { value: "extended", label: getQuestionTypeLabel("extended") },
];

const defaultOptions = [
  { id: "a", text: "Вариант A" },
  { id: "b", text: "Вариант B" },
];

function getLetter(index: number) {
  return String.fromCharCode(97 + index);
}

function buildPayload(type: QuestionType, options: Array<{ id: string; text: string }>, correctOption: string, correctOptions: string[], correctAnswers: string[]) {
  if (type === "single") {
    return { options, correct_option: correctOption || options[0]?.id };
  }
  if (type === "multiple") {
    return { options, correct_options: correctOptions.length ? correctOptions : [options[0]?.id].filter(Boolean) };
  }
  if (type === "text") {
    return { correct_answers: correctAnswers.filter((item) => item.trim()) };
  }
  return {};
}

interface Props {
  isOpen: boolean;
  categories: Category[];
  question?: QuestionForm | null;
  onClose: () => void;
  onSave: (question: QuestionForm) => void;
}

export function QuestionFormModal({ isOpen, categories, question, onClose, onSave }: Props) {
  const [title, setTitle] = useState("");
  const [prompt, setPrompt] = useState("");
  const [questionType, setQuestionType] = useState<QuestionType>("single");
  const [basePoints, setBasePoints] = useState("1");
  const [categoryId, setCategoryId] = useState<number | null>(null);
  const [options, setOptions] = useState<Array<{ id: string; text: string }>>(defaultOptions);
  const [correctOption, setCorrectOption] = useState("a");
  const [correctOptions, setCorrectOptions] = useState<string[]>(["a"]);
  const [correctAnswers, setCorrectAnswers] = useState<string[]>([""]);

  useEffect(() => {
    if (!question) {
      setTitle("");
      setPrompt("");
      setQuestionType("single");
      setBasePoints("1");
      setCategoryId(null);
      setOptions(defaultOptions);
      setCorrectOption("a");
      setCorrectOptions(["a"]);
      setCorrectAnswers([""]);
      return;
    }

    setTitle(question.title);
    setPrompt(question.prompt);
    setQuestionType(question.question_type);
    setBasePoints(String(question.base_points ?? "1"));
    setCategoryId(question.category ?? null);

    const payload = question.payload || {};
    if (question.question_type === "single") {
      setOptions(Array.isArray(payload.options) && payload.options.length ? payload.options : defaultOptions);
      setCorrectOption(payload.correct_option || payload.options?.[0]?.id || "a");
    } else if (question.question_type === "multiple") {
      setOptions(Array.isArray(payload.options) && payload.options.length ? payload.options : defaultOptions);
      setCorrectOptions(Array.isArray(payload.correct_options) && payload.correct_options.length ? payload.correct_options : [payload.options?.[0]?.id || "a"]);
    } else if (question.question_type === "text") {
      setCorrectAnswers(Array.isArray(payload.correct_answers) && payload.correct_answers.length ? payload.correct_answers : [""]);
    } else {
      setOptions(defaultOptions);
      setCorrectOption("a");
      setCorrectOptions(["a"]);
      setCorrectAnswers([""]);
    }
  }, [question, isOpen]);

  const isSaveDisabled = useMemo(() => {
    if (!title.trim() || !prompt.trim()) {
      return true;
    }
    if (!Number(basePoints) || Number(basePoints) < 0) {
      return true;
    }
    if (questionType === "single") {
      return options.length < 2 || !options.every((opt) => opt.text.trim()) || !correctOption;
    }
    if (questionType === "multiple") {
      return options.length < 2 || !options.every((opt) => opt.text.trim()) || correctOptions.length === 0;
    }
    if (questionType === "text") {
      return correctAnswers.filter((item) => item.trim()).length === 0;
    }
    return false;
  }, [title, prompt, basePoints, questionType, options, correctOption, correctOptions, correctAnswers]);

  function changeOption(index: number, value: string) {
    const next = [...options];
    next[index] = { ...next[index], text: value };
    setOptions(next);
  }

  function addOption() {
    setOptions((prev) => [...prev, { id: getLetter(prev.length), text: "" }]);
  }

  function removeOption(index: number) {
    setOptions((prev) => {
      const next = prev.filter((_, idx) => idx !== index);
      return next;
    });
  }

  function changeCorrectOption(id: string) {
    setCorrectOption(id);
  }

  function toggleCorrectOption(id: string) {
    setCorrectOptions((prev) => {
      if (prev.includes(id)) {
        return prev.filter((item) => item !== id);
      }
      return [...prev, id];
    });
  }

  function changeAnswer(index: number, value: string) {
    const next = [...correctAnswers];
    next[index] = value;
    setCorrectAnswers(next);
  }

  function addAnswer() {
    setCorrectAnswers((prev) => [...prev, ""]);
  }

  function removeAnswer(index: number) {
    setCorrectAnswers((prev) => prev.filter((_, idx) => idx !== index));
  }

  async function handleSave() {
    const payload = buildPayload(questionType, options, correctOption, correctOptions, correctAnswers);
    onSave({
      id: question?.id,
      title: title.trim(),
      prompt: prompt.trim(),
      question_type: questionType,
      base_points: basePoints,
      category: categoryId,
      payload,
    });
  }

  return (
    <Modal
      isOpen={isOpen}
      title={question ? "Редактировать вопрос" : "Создать вопрос"}
      description="Заполните поля для вопроса и сохраните изменения."
      onClose={onClose}
      actions={
        <>
          <button type="button" className="button button-secondary" onClick={onClose}>
            Отмена
          </button>
          <button type="button" className="button button-primary" onClick={handleSave} disabled={isSaveDisabled}>
            Сохранить
          </button>
        </>
      }
    >
      <div className={styles.grid}>
        <label className={styles.field}>
          <span>Название</span>
          <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Название вопроса" />
        </label>

        <label className={styles.field}>
          <span>Текст вопроса</span>
          <textarea value={prompt} onChange={(e) => setPrompt(e.target.value)} rows={4} placeholder="Формулировка для студента" />
        </label>

        <label className={styles.field}>
          <span>Тип вопроса</span>
          <select value={questionType} onChange={(e) => setQuestionType(e.target.value as QuestionType)}>
            {questionTypeOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        <label className={styles.field}>
          <span>Баллы</span>
          <input
            type="number"
            value={basePoints}
            min="0"
            step="0.5"
            onChange={(e) => setBasePoints(e.target.value)}
          />
        </label>

        <label className={styles.field}>
          <span>Категория</span>
          <select value={categoryId ?? ""} onChange={(e) => setCategoryId(e.target.value ? Number(e.target.value) : null)}>
            <option value="">Без категории</option>
            {categories.map((category) => (
              <option key={category.id} value={category.id}>
                {category.title}
              </option>
            ))}
          </select>
        </label>
      </div>

      {questionType === "single" && (
        <div className={styles.section}>
          <h4>Варианты ответа</h4>
          {options.map((option, index) => (
            <div key={option.id} className={styles.inlineRow}>
              <label>
                <input type="radio" name="single-correct" checked={correctOption === option.id} onChange={() => changeCorrectOption(option.id)} />
                <span>{option.id}</span>
              </label>
              <input
                value={option.text}
                onChange={(e) => changeOption(index, e.target.value)}
                placeholder={`Вариант ${getLetter(index).toUpperCase()}`}
              />
              {options.length > 2 && (
                <button type="button" className="button button-secondary" onClick={() => removeOption(index)}>
                  Удалить
                </button>
              )}
            </div>
          ))}
          <button type="button" className="button button-secondary button-full" onClick={addOption}>
            Добавить вариант
          </button>
        </div>
      )}

      {questionType === "multiple" && (
        <div className={styles.section}>
          <h4>Варианты ответа</h4>
          {options.map((option, index) => (
            <div key={option.id} className={styles.inlineRow}>
              <label>
                <input type="checkbox" checked={correctOptions.includes(option.id)} onChange={() => toggleCorrectOption(option.id)} />
                <span>{option.id}</span>
              </label>
              <input
                value={option.text}
                onChange={(e) => changeOption(index, e.target.value)}
                placeholder={`Вариант ${getLetter(index).toUpperCase()}`}
              />
              {options.length > 2 && (
                <button type="button" className="button button-secondary" onClick={() => removeOption(index)}>
                  Удалить
                </button>
              )}
            </div>
          ))}
          <button type="button" className="button button-secondary button-full" onClick={addOption}>
            Добавить вариант
          </button>
        </div>
      )}

      {questionType === "text" && (
        <div className={styles.section}>
          <h4>Допустимые ответы</h4>
          {correctAnswers.map((value, index) => (
            <div key={index} className={styles.inlineRow}>
              <input
                value={value}
                onChange={(e) => changeAnswer(index, e.target.value)}
                placeholder="Ответ"
              />
              {correctAnswers.length > 1 && (
                <button type="button" className="button button-secondary" onClick={() => removeAnswer(index)}>
                  Удалить
                </button>
              )}
            </div>
          ))}
          <button type="button" className="button button-secondary button-full" onClick={addAnswer}>
            Добавить ответ
          </button>
        </div>
      )}

      {questionType === "extended" && (
        <div className={styles.section}>
          <h4>Развёрнутый вопрос</h4>
          <p>Дополнительная структура не нужна, студент вводит развёрнутый ответ.</p>
        </div>
      )}
    </Modal>
  );
}
