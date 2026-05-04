import styles from "./SectionHeader.module.css";

type Props = {
  eyebrow?: string;
  title: string;
  description: string;
};

export function SectionHeader({ eyebrow, title, description }: Props) {
  return (
    <header className={styles.header}>
      {eyebrow ? <span className={styles.eyebrow}>{eyebrow}</span> : null}
      <h1>{title}</h1>
      <p>{description}</p>
    </header>
  );
}
