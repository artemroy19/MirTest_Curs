import { FormEvent, useEffect, useState } from "react";
import { apiClient } from "../../api/client";
import { ConfirmModal } from "../../components/common/ConfirmModal/ConfirmModal";
import { EmptyState } from "../../components/common/EmptyState/EmptyState";
import { Modal } from "../../components/common/Modal/Modal";
import { SectionHeader } from "../../components/layout/SectionHeader/SectionHeader";
import { extractList } from "../../utils/extractList";
import styles from "./TeacherGroupsPage.module.css";

type Group = {
  id: number;
  title: string;
  description: string;
  invite_code: string;
  students_count: number;
};

type User = {
  id: number;
  first_name: string;
  last_name: string;
  email: string;
};

export function TeacherGroupsPage() {
  const [groups, setGroups] = useState<Group[]>([]);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [selectedGroup, setSelectedGroup] = useState<Group | null>(null);
  const [groupMembers, setGroupMembers] = useState<User[]>([]);
  const [toast, setToast] = useState("");
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<Group | null>(null);

  useEffect(() => {
    async function load() {
      const response = await apiClient.get("/groups/");
      setGroups(extractList(response.data));
    }
    void load();
  }, []);

  async function createGroup(event: React.FormEvent) {
    event.preventDefault();
    try {
      await apiClient.post("/groups/", { title, description });
      setToast("Группа создана.");
      setTitle("");
      setDescription("");
      const response = await apiClient.get("/groups/");
      setGroups(extractList(response.data));
    } catch {
      setToast("Не удалось создать группу.");
    }
  }

  async function deleteGroup() {
    if (!deleteTarget) return;
    await apiClient.delete(`/groups/${deleteTarget.id}/`);
    setGroups((prev) => prev.filter((item) => item.id !== deleteTarget.id));
    setDeleteTarget(null);
    setConfirmOpen(false);
  }

  async function handleViewGroup(group: Group) {
    setSelectedGroup(group);
    try {
      const membershipsRes = await apiClient.get("/group-memberships/", { params: { group: group.id } });
      const memberIds = extractList(membershipsRes.data).map((membership: any) => membership.student);
      if (memberIds.length === 0) {
        setGroupMembers([]);
        return;
      }

      const usersRes = await apiClient.get("/users/", { params: { ids: memberIds.join(",") } });
      setGroupMembers(extractList(usersRes.data));
    } catch {
      setToast("Не удалось загрузить участников группы.");
    }
  }

  async function removeStudentFromGroup(groupId: number, studentId: number) {
    try {
      const membershipsRes = await apiClient.get("/group-memberships/", { params: { group: groupId, student: studentId } });
      const membershipId = (extractList(membershipsRes.data) as any[])?.[0]?.id;
      if (!membershipId) return;
      await apiClient.delete(`/group-memberships/${membershipId}/`);
      if (selectedGroup) {
        await handleViewGroup(selectedGroup);
      }
    } catch {
      setToast("Не удалось удалить студента из группы.");
    }
  }

  return (
    <div className="ui-page">
      <SectionHeader title="Мои группы" description="Создавайте группы, копируйте код и управляйте составом студентов." />
      <div className="ui-split">
        <section className={`${styles.groupPanel} ui-card`}>
          <h3>Создать группу</h3>
          <form className={styles.form} onSubmit={createGroup}>
            <label>
              Название группы
              <input value={title} onChange={(e) => setTitle(e.target.value)} required />
            </label>
            <label>
              Описание
              <textarea value={description} onChange={(e) => setDescription(e.target.value)} />
            </label>
            <button type="submit" className="button button-primary button-full">
              Создать группу
            </button>
          </form>
        </section>

        <section className={`${styles.groupPanel} ui-card`}>
          <h3>Список групп</h3>
          {groups.length === 0 ? (
            <EmptyState
              title="Групп пока нет"
              description="Создайте первую группу, чтобы приглашать студентов и назначать тесты."
              actionLabel="Создать первую группу"
              onAction={() => document.querySelector("input")?.focus()}
            />
          ) : (
            <div className={styles.groupsList}>
              {groups.map((group) => (
                <article key={group.id} className={styles.groupCard}>
                  <div>
                    <h4>{group.title}</h4>
                    <p>{group.description}</p>
                    <div className={styles.codeRow}>
                      <code>{group.invite_code}</code>
                      <button type="button" className="button button-secondary" onClick={() => navigator.clipboard.writeText(group.invite_code)}>
                        Копировать
                      </button>
                    </div>
                  </div>
                  <div className={styles.cardFooter}>
                    <span>Студентов: {group.students_count}</span>
                    <div className={styles.cardActions}>
                      <button type="button" className="button button-secondary" onClick={() => void handleViewGroup(group)}>
                        Участники
                      </button>
                      <button
                        type="button"
                        className="button button-danger"
                        onClick={() => {
                          setDeleteTarget(group);
                          setConfirmOpen(true);
                        }}
                      >
                        Удалить
                      </button>
                    </div>
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>
      </div>
      <ConfirmModal
        isOpen={confirmOpen}
        title="Удалить группу?"
        description="Это действие удалит группу и отменит доступ студентов. Продолжить?"
        onCancel={() => setConfirmOpen(false)}
        onConfirm={deleteGroup}
        danger
      />

      <Modal
        isOpen={Boolean(selectedGroup)}
        title={`Группа: ${selectedGroup?.title}`}
        onClose={() => setSelectedGroup(null)}
        actions={
          <>
            <button type="button" className="button button-secondary" onClick={() => setSelectedGroup(null)}>
              Закрыть
            </button>
          </>
        }
      >
        <p>Код группы: {selectedGroup?.invite_code}</p>
        <h4>Студенты ({groupMembers.length})</h4>
        {groupMembers.length === 0 ? (
          <EmptyState title="В группе пока нет студентов" description="Поделитесь кодом группы, чтобы студенты могли присоединиться." />
        ) : (
          <ul className={styles.memberList}>
            {groupMembers.map((student) => (
              <li key={student.id} className={styles.memberItem}>
                <span>{student.first_name} {student.last_name} ({student.email})</span>
                <button type="button" className="button button-danger" onClick={() => void removeStudentFromGroup(selectedGroup!.id, student.id)}>
                  Удалить
                </button>
              </li>
            ))}
          </ul>
        )}
      </Modal>
      {toast ? <div className="ui-success">{toast}</div> : null}
    </div>
  );
}
