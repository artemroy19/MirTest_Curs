import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { apiClient } from "../../api/client";
import { EmptyState } from "../../components/common/EmptyState/EmptyState";
import { Modal } from "../../components/common/Modal/Modal";
import { SectionHeader } from "../../components/layout/SectionHeader/SectionHeader";
import { extractList } from "../../utils/extractList";
import styles from "./TeacherTestsPage.module.css";

type TestItem = {
  id: number;
  title: string;
  description: string;
  timer_minutes: number | null;
  attempts_limit: number | null;
  deadline: string | null;
  questions_count: number;
};

type Group = {
  id: number;
  title: string;
};

type Student = {
  id: number;
  first_name: string;
  last_name: string;
  email: string;
};

type Membership = {
  id: number;
  group: number;
  student: number;
};

type Assignment = {
  id: number;
  group: number | null;
  student: number | null;
};

type AssignTab = "groups" | "students";

function formatStudentName(student: Student) {
  return `${student.last_name} ${student.first_name}`.trim() || student.email;
}

export function TeacherTestsPage() {
  const navigate = useNavigate();
  const [tests, setTests] = useState<TestItem[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [assignOpen, setAssignOpen] = useState(false);
  const [selectedTest, setSelectedTest] = useState<TestItem | null>(null);
  const [groups, setGroups] = useState<Group[]>([]);
  const [students, setStudents] = useState<Student[]>([]);
  const [memberships, setMemberships] = useState<Membership[]>([]);
  const [selectedGroupIds, setSelectedGroupIds] = useState<number[]>([]);
  const [manualStudentIds, setManualStudentIds] = useState<number[]>([]);
  const [savingAssignment, setSavingAssignment] = useState(false);
  const [success, setSuccess] = useState("");
  const [assignTab, setAssignTab] = useState<AssignTab>("groups");
  const [expandedGroupIds, setExpandedGroupIds] = useState<number[]>([]);

  async function loadTests() {
    setLoading(true);
    setError("");
    try {
      const response = await apiClient.get("/tests/");
      setTests(extractList(response.data));
    } catch {
      setError("Не удалось загрузить список тестов.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadTests();
  }, []);

  const membershipsByGroup = useMemo(() => {
    const map = new Map<number, number[]>();
    memberships.forEach((membership) => {
      const current = map.get(membership.group) ?? [];
      map.set(membership.group, [...current, membership.student]);
    });
    return map;
  }, [memberships]);

  const selectedStudentIds = useMemo(() => {
    const ids = new Set<number>(manualStudentIds);
    selectedGroupIds.forEach((groupId) => {
      (membershipsByGroup.get(groupId) ?? []).forEach((studentId) => ids.add(studentId));
    });
    return Array.from(ids);
  }, [manualStudentIds, membershipsByGroup, selectedGroupIds]);

  async function openAssignModal(test: TestItem) {
    setSelectedTest(test);
    setAssignOpen(true);
    setError("");
    setSuccess("");
    setAssignTab("groups");
    try {
      const [groupsRes, studentsRes, membershipsRes, assignmentsRes] = await Promise.all([
        apiClient.get("/groups/"),
        apiClient.get("/users/", { params: { role: "student" } }),
        apiClient.get("/group-memberships/"),
        apiClient.get("/assignments/", { params: { test: test.id } }),
      ]);

      const teacherMemberships = extractList<Membership>(membershipsRes.data);
      const groupStudentIds = new Set(teacherMemberships.map((membership) => membership.student));
      const groupStudents = extractList<Student>(studentsRes.data).filter((student) => groupStudentIds.has(student.id));

      setGroups(extractList(groupsRes.data));
      setStudents(groupStudents);
      setMemberships(teacherMemberships);

      const assignments = extractList<Assignment>(assignmentsRes.data);
      setSelectedGroupIds(assignments.flatMap((assignment) => (assignment.group ? [assignment.group] : [])));
      setManualStudentIds(assignments.flatMap((assignment) => (assignment.student && groupStudentIds.has(assignment.student) ? [assignment.student] : [])));
      setExpandedGroupIds(assignments.flatMap((assignment) => (assignment.group ? [assignment.group] : [])));
    } catch {
      setError("Не удалось загрузить данные для назначения теста.");
    }
  }

  function getGroupStudentIds(groupId: number) {
    return membershipsByGroup.get(groupId) ?? [];
  }

  function toggleGroup(groupId: number, checked: boolean) {
    setSelectedGroupIds((previous) =>
      checked ? Array.from(new Set([...previous, groupId])) : previous.filter((id) => id !== groupId),
    );
  }

  function toggleGroupStudent(studentId: number, checked: boolean) {
    setManualStudentIds((previous) =>
      checked ? Array.from(new Set([...previous, studentId])) : previous.filter((id) => id !== studentId),
    );
  }

  async function handleAssign() {
    if (!selectedTest) {
      return;
    }
    if (selectedGroupIds.length === 0 && selectedStudentIds.length === 0) {
      setError("Выберите хотя бы одну группу или одного студента.");
      return;
    }

    try {
      setSavingAssignment(true);
      setError("");
      await apiClient.post(`/tests/${selectedTest.id}/assign/`, {
        group_ids: selectedGroupIds,
        student_ids: manualStudentIds.filter(
          (studentId) =>
            !selectedGroupIds.some((groupId) => (membershipsByGroup.get(groupId) ?? []).includes(studentId)),
        ),
      });
      setAssignOpen(false);
      setSuccess("Тест успешно назначен.");
    } catch {
      setError("Не удалось сохранить назначение теста.");
    } finally {
      setSavingAssignment(false);
    }
  }

  async function handleDelete(testId: number) {
    if (!window.confirm("Удалить тест? Это действие нельзя отменить.")) {
      return;
    }
    try {
      await apiClient.delete(`/tests/${testId}/`);
      await loadTests();
    } catch {
      setError("Не удалось удалить тест.");
    }
  }

  const filteredTests = useMemo(() => {
    const normalized = search.trim().toLowerCase();
    if (!normalized) {
      return tests;
    }
    return tests.filter(
      (test) =>
        test.title.toLowerCase().includes(normalized) ||
        test.description.toLowerCase().includes(normalized),
    );
  }, [search, tests]);

  return (
    <div className={styles.page}>
      <SectionHeader
        title="Мои тесты"
        description="Создавайте тесты, редактируйте их структуру и назначайте студентам."
      />

      <div className={styles.toolbar}>
        <input
          className={styles.search}
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Поиск по названию или описанию"
        />
        <button type="button" className={`button button-primary ${styles.createTestButton}`} onClick={() => navigate("/teacher/tests/new")}>
          Создать тест
        </button>
      </div>

      {error ? <div className={styles.error}>{error}</div> : null}
      {success ? <div className={styles.success}>{success}</div> : null}

      {loading ? <div className={styles.info}>Загрузка тестов...</div> : null}

      {!loading && tests.length === 0 ? (
        <EmptyState
          title="У вас пока нет тестов"
          description="Создайте первый тест, чтобы он появился в списке."
          actionLabel="Создать первый тест"
          onAction={() => navigate("/teacher/tests/new")}
        />
      ) : null}

      {!loading && tests.length > 0 && filteredTests.length === 0 ? (
        <EmptyState title="Ничего не найдено" description="Попробуйте изменить параметры поиска." />
      ) : null}

      {!loading && filteredTests.length > 0 ? (
        <div className={styles.grid}>
          {filteredTests.map((test) => (
            <article key={test.id} className={styles.card}>
              <div className={styles.cardHeader}>
                <div>
                  <h3>{test.title}</h3>
                  <p>{test.description || "Описание не указано."}</p>
                </div>
                <span className={styles.questionsBadge}>{test.questions_count} вопросов</span>
              </div>

              <div className={styles.meta}>
                <span>{test.timer_minutes ? `${test.timer_minutes} мин` : "Без таймера"}</span>
                <span>
                  {test.attempts_limit == null ? "Без лимита попыток" : `Попыток: ${test.attempts_limit}`}
                </span>
                <span>
                  {test.deadline ? `До ${new Date(test.deadline).toLocaleString("ru-RU")}` : "Без дедлайна"}
                </span>
              </div>

              <div className={styles.actions}>
                <button type="button" className="button button-secondary" onClick={() => navigate(`/teacher/tests/${test.id}/edit`)}>
                  Редактировать
                </button>
                <button type="button" className="button button-secondary" onClick={() => void openAssignModal(test)}>
                  Назначить
                </button>
                <button type="button" className="button button-danger" onClick={() => void handleDelete(test.id)}>
                  Удалить
                </button>
              </div>
            </article>
          ))}
        </div>
      ) : null}

      <Modal
        isOpen={assignOpen}
        title={selectedTest ? `Назначение теста "${selectedTest.title}"` : "Назначение теста"}
        onClose={() => setAssignOpen(false)}
        actions={
          <>
            <button type="button" className="button button-secondary" onClick={() => setAssignOpen(false)}>
              Закрыть
            </button>
            <button type="button" className="button button-primary" disabled={savingAssignment} onClick={() => void handleAssign()}>
              Сохранить
            </button>
          </>
        }
      >
        <div className={styles.assignSummary}>
          <span>Выбрано групп: {selectedGroupIds.length}</span>
          <span>Выбрано студентов: {selectedStudentIds.length}</span>
        </div>

        <div className={styles.tabRow}>
          <button
            type="button"
            className={`${styles.tabButton} ${assignTab === "groups" ? styles.activeTab : ""}`}
            onClick={() => setAssignTab("groups")}
          >
            Группы
          </button>
          <button
            type="button"
            className={`${styles.tabButton} ${assignTab === "students" ? styles.activeTab : ""}`}
            onClick={() => setAssignTab("students")}
          >
            Студенты
          </button>
        </div>

        {assignTab === "groups" ? (
          <section className={styles.assignPanel}>
            {groups.length === 0 ? (
              <EmptyState title="Групп пока нет" description="Создайте группу, чтобы массово назначать тесты." />
            ) : (
              <div className={styles.groupList}>
                {groups.map((group) => {
                  const groupStudentIds = getGroupStudentIds(group.id);
                  const assignedWholeGroup = selectedGroupIds.includes(group.id);
                  const expanded = expandedGroupIds.includes(group.id);

                  return (
                    <article key={group.id} className={styles.groupCard}>
                      <div className={styles.groupHeader}>
                        <label className={styles.groupToggle}>
                          <input
                            type="checkbox"
                            checked={assignedWholeGroup}
                            onChange={(event) => toggleGroup(group.id, event.target.checked)}
                          />
                          <span>Назначить всей группе</span>
                        </label>
                        <div className={styles.groupMeta}>
                          <strong>{group.title}</strong>
                          <span>{groupStudentIds.length} студентов</span>
                        </div>
                        <button
                          type="button"
                          className={styles.expandButton}
                          onClick={() =>
                            setExpandedGroupIds((previous) =>
                              expanded
                                ? previous.filter((id) => id !== group.id)
                                : [...previous, group.id],
                            )
                          }
                        >
                          {expanded ? "Свернуть" : "Развернуть"}
                        </button>
                      </div>

                      {expanded ? (
                        <div className={styles.groupStudents}>
                          {groupStudentIds.length === 0 ? (
                            <span className={styles.emptyInline}>В этой группе пока нет студентов.</span>
                          ) : (
                            groupStudentIds.map((studentId) => {
                              const student = students.find((item) => item.id === studentId);
                              if (!student) {
                                return null;
                              }
                              const selectedIndividually = manualStudentIds.includes(studentId);
                              const selectedByGroup = assignedWholeGroup;
                              return (
                                <label key={studentId} className={styles.studentRow}>
                                  <input
                                    type="checkbox"
                                    checked={selectedByGroup || selectedIndividually}
                                    onChange={(event) => toggleGroupStudent(studentId, event.target.checked)}
                                  />
                                  <span>{formatStudentName(student)}</span>
                                  {selectedByGroup ? <em className={styles.groupMark}>Из группы</em> : null}
                                </label>
                              );
                            })
                          )}
                        </div>
                      ) : null}
                    </article>
                  );
                })}
              </div>
            )}
          </section>
        ) : (
          <section className={styles.assignPanel}>
            {students.length === 0 ? (
              <EmptyState title="Студентов пока нет" description="Добавьте студентов, чтобы назначать им тесты." />
            ) : (
              <div className={styles.studentList}>
                {students.map((student) => {
                  const viaGroup = selectedGroupIds.some((groupId) => getGroupStudentIds(groupId).includes(student.id));
                  return (
                    <label key={student.id} className={styles.studentRow}>
                      <input
                        type="checkbox"
                        checked={selectedStudentIds.includes(student.id)}
                        onChange={(event) => toggleGroupStudent(student.id, event.target.checked)}
                      />
                      <span>{formatStudentName(student)}</span>
                      {viaGroup ? <em className={styles.groupMark}>Уже входит в выбранную группу</em> : null}
                    </label>
                  );
                })}
              </div>
            )}
          </section>
        )}
      </Modal>
    </div>
  );
}
