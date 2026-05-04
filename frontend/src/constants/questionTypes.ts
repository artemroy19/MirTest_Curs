import { QuestionType } from "../types/domain";

export const QUESTION_TYPE_LABELS: Record<QuestionType, string> = {
  single: "Одиночный выбор",
  multiple: "Множественный выбор",
  text: "Краткий ответ",
  extended: "Развёрнутый вопрос",
};

export const getQuestionTypeLabel = (type: QuestionType): string => {
  return QUESTION_TYPE_LABELS[type] || type;
};
