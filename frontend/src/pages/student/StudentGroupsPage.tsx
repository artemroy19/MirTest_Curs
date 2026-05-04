import { FormEvent, useEffect, useMemo, useState } from "react";

import { apiClient } from "../../api/client";
import { EmptyState } from "../../components/common/EmptyState/EmptyState";
import { SectionHeader } from "../../components/layout/SectionHeader/SectionHeader";
import { useSessionStore } from "../../store/sessionStore";
import styles from "./StudentGroupsPage.module.css";

type Group = {
  id: number;
  title: string;
  description: string;
  invite_code: string;
  members_count: number;
};

type Membership = {
  id: number;
  group: number;
  group_title: string;
  student: number;
  student_email: string;
};

export function GroupsPage() {
  const role = useSessionStore((s) => s.user?.role);
  const [groups, setGroups] = useState<Group[]>([]);
  const [memberships, setMemberships] = useState<Membership[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [joinCode, setJoinCode] = useState("");

  const isTeacher = role === "teacher" || role === "admin";
  const isStudent = role === "student";

  function parseError(e: any, fallback: string) {
    const data = e?.response?.data;
    if (!data) return fallback;
    if (typeof data === "string") return data;
    if (data.detail) return data.detail;
    return Object.values(data).flat().join(" ");
  }

  const membershipsByGroup = useMemo(() => {
    const map = new Map<number, Membership[]>();
    memberships.forEach((item) => {
      map.set(item.group, [...(map.get(item.group) || []), item]);
    });
    return map;
  }, [memberships]);

  async function load() {
    setLoading(true);
    setError("");
    try {
      const [groupsRes, membershipsRes] = await Promise.all([
        apiClient.get("/groups/"),
        apiClient.get("/group-memberships/")
      ]);
      const groupsData = groupsRes.data.results || groupsRes.data;
      const membershipsData = membershipsRes.data.results || membershipsRes.data;
      setGroups(groupsData);
      setMemberships(membershipsData);
    } catch {
      setError("Не удалось загрузить группы");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function createGroup(event: FormEvent) {
    event.preventDefault();
    if (!title.trim()) return;
    try {
      await apiClient.post("/groups/", { title, description });
      setTitle("");
      setDescription("");
      await load();
    } catch (e: any) {
      setError(parseError(e, "Не удалось создать группу"));
    }
  }

  async function joinGroup(event: FormEvent) {
    event.preventDefault();
    if (!joinCode.trim()) return;
    try {
      await apiClient.post("/groups/join/", { invite_code: joinCode });
      setJoinCode("");
      await load();
    } catch (e: any) {
      setError(parseError(e, "Код приглашения недействителен"));
    }
  }

  async function regenerateCode(groupId: number) {
    try {
      await apiClient.post(`/groups/${groupId}/regenerate-code/`);
      await load();
    } catch (e: any) {
      setError(parseError(e, "Не удалось обновить код"));
    }
  }

  async function leaveGroup(groupId: number) {
    try {
      await apiClient.post("/group-memberships/leave/", { group: groupId });
      await load();
    } catch (e: any) {
      setError(parseError(e, "Не удалось выйти из группы"));
    }
  }

  async function removeMembership(id: number) {
    try {
      await apiClient.delete(`/group-memberships/${id}/`);
      await load();
    } catch (e: any) {
      setError(parseError(e, "Не удалось удалить участника"));
    }
  }

  return (
    <div className={styles.page}>
      <SectionHeader
        eyebrow="Группы"
        title={isStudent ? "Мои группы" : "Группы и коды приглашения"}
        description={
          isStudent
            ? "Вступайте в группы по коду и следите за своими учебными группами в одном месте."
            : "Создавайте группы, обновляйте коды приглашения и управляйте составом студентов."
        }
      />

      {error ? <div className={styles.error}>{error}</div> : null}
      {loading ? <div className={styles.info}>Загрузка групп...</div> : null}

      {isTeacher && (
        <section className={styles.heroGrid}>
          <article className={styles.card}>
            <div className={styles.cardHeader}>
              <h3>Создать группу</h3>
              <p>Подготовьте группу и выдайте студентам код приглашения.</p>
            </div>
            <form className={styles.form} onSubmit={createGroup}>
              <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Название группы" required />
              <textarea value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Краткое описание группы" />
              <button type="submit" className="button button-primary">
                Создать группу
              </button>
            </form>
          </article>
        </section>
      )}

      {isStudent && (
        <section className={styles.heroGrid}>
          <article className={styles.joinCard}>
            <div className={styles.cardHeader}>
              <h3>Присоединиться по коду</h3>
              <p>Введите код, который вы получили от преподавателя.</p>
            </div>
            <form className={styles.joinForm} onSubmit={joinGroup}>
              <input
                value={joinCode}
                onChange={(e) => setJoinCode(e.target.value.toUpperCase())}
                placeholder="Например: ABC123"
                maxLength={32}
              />
              <button type="submit" className="button button-primary">
                Вступить в группу
              </button>
            </form>
          </article>
        </section>
      )}

      <section className={styles.listSection}>
        {groups.length === 0 ? (
          <EmptyState
            title={isStudent ? "Вы пока не состоите ни в одной группе" : "Групп пока нет"}
            description={isStudent ? "Введите код приглашения, чтобы присоединиться к группе." : "Создайте первую группу, чтобы начать работу."}
          />
        ) : (
          <div className={styles.grid}>
            {groups.map((group) => (
              <article className={styles.card} key={group.id}>
                <div className={styles.cardHeader}>
                  <div>
                    <h3>{group.title}</h3>
                    <p>{group.description || "Описание пока не добавлено."}</p>
                  </div>
                  <span className={styles.badge}>{group.members_count} участников</span>
                </div>

                <div className={styles.meta}>
                  <div>
                    <dt>Код приглашения</dt>
                    <dd>{group.invite_code}</dd>
                  </div>
                  <div>
                    <dt>Статус</dt>
                    <dd>{isStudent ? "Вы состоите в группе" : "Группа активна"}</dd>
                  </div>
                </div>

                <div className={styles.actions}>
                  {isTeacher && (
                    <button type="button" className="button button-secondary" onClick={() => regenerateCode(group.id)}>
                      Обновить код
                    </button>
                  )}

                  {isStudent && (
                    <button type="button" className="button button-danger" onClick={() => leaveGroup(group.id)}>
                      Выйти из группы
                    </button>
                  )}
                </div>

                {isTeacher && membershipsByGroup.get(group.id)?.length ? (
                  <div className={styles.membersBlock}>
                    <h4>Состав группы</h4>
                    <ul className={styles.memberList}>
                      {(membershipsByGroup.get(group.id) || []).map((member) => (
                        <li key={member.id} className={styles.memberItem}>
                          <span>{member.student_email}</span>
                          <button type="button" className="button button-danger" onClick={() => removeMembership(member.id)}>
                            Удалить
                          </button>
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : null}
              </article>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
