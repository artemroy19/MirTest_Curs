import { QuestionType } from "../../../types/domain";
import { getQuestionTypeLabel } from "../../../constants/questionTypes";
import styles from "./QuestionCard.module.css";

type Question = {
  id: number;
  title: string;
  prompt: string;
  question_type: QuestionType;
  base_points: number | string;
  payload: any;
  category?: { id: number; title: string } | null;
};

interface Props {
  question: Question;
  onPreview: (question: Question) => void;
  onEdit: (question: Question) => void;
  onDelete: (question: Question) => void;
}

export function QuestionCard({ question, onPreview, onEdit, onDelete }: Props) {
  return (
    <article className={styles.card} onClick={() => onPreview(question)}>
      <div className={styles.main}>
        <div className={styles.topLine}>
          <span className={styles.typeBadge}>{getQuestionTypeLabel(question.question_type)}</span>
          <span className={styles.points}>{question.base_points} балл{Number(question.base_points) === 1 ? "" : "ов"}</span>
        </div>
        <h3 className={styles.title}>{question.title}</h3>
        <p className={styles.prompt}>{question.prompt}</p>
      </div>
      <div className={styles.actions} onClick={(event) => event.stopPropagation()}>
        <button type="button" className="button button-secondary" onClick={() => onEdit(question)}>
          Редактировать
        </button>
        <button type="button" className="button button-danger" onClick={() => onDelete(question)}>
          Удалить
        </button>
      </div>
    </article>
  );
}
