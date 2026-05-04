import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { AppLayout } from "../layout/AppLayout";
import { useSessionStore } from "../store/sessionStore";
import { GroupsPage } from "../pages/student/StudentGroupsPage";
import { LoginPage } from "../pages/auth/LoginPage";
import { RegisterPage } from "../pages/auth/RegisterPage";
import { ProfilePage } from "../pages/common/ProfilePage";
import { StudentTestsPage } from "../pages/student/StudentTestsPage";
import { QuestionBankPage } from "../pages/teacher/QuestionBankPage";
import { ResultsPage } from "../pages/student/StudentResultsPage";
import { TeacherTestsPage } from "../pages/teacher/TeacherTestsPage";
import { TeacherTestConstructorPage } from "../pages/teacher/TeacherTestConstructorPage";
import { TeacherGroupsPage } from "../pages/teacher/TeacherGroupsPage";
import { TeacherResultsPage } from "../pages/teacher/TeacherResultsPage";
import { TestTakingPage } from "../pages/student/TestTakingPage";
import { getDefaultRoute } from "../utils/routes";

function ProtectedLayout() {
  const isAuthenticated = useSessionStore((s) => s.isAuthenticated);
  return isAuthenticated ? <AppLayout /> : <Navigate to="/login" replace />;
}

function LoginRoute() {
  const isAuthenticated = useSessionStore((s) => s.isAuthenticated);
  const role = useSessionStore((s) => s.user?.role);
  return isAuthenticated ? <Navigate to={getDefaultRoute(role)} replace /> : <LoginPage />;
}

function RegisterRoute() {
  const isAuthenticated = useSessionStore((s) => s.isAuthenticated);
  const role = useSessionStore((s) => s.user?.role);
  return isAuthenticated ? <Navigate to={getDefaultRoute(role)} replace /> : <RegisterPage />;
}

function IndexRoute() {
  const role = useSessionStore((s) => s.user?.role);
  return <Navigate to={getDefaultRoute(role)} replace />;
}

export function AppRouter() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginRoute />} />
        <Route path="/register" element={<RegisterRoute />} />
        <Route path="/" element={<ProtectedLayout />}>
          <Route index element={<IndexRoute />} />
          <Route path="tests" element={<StudentTestsPage />} />
          <Route path="groups" element={<GroupsPage />} />
          <Route path="results" element={<ResultsPage />} />
          <Route path="profile" element={<ProfilePage />} />
          <Route path="test/:testId/attempt/:attemptId" element={<TestTakingPage />} />
          <Route path="teacher/tests" element={<TeacherTestsPage />} />
          <Route path="teacher/tests/new" element={<TeacherTestConstructorPage />} />
          <Route path="teacher/tests/:testId/edit" element={<TeacherTestConstructorPage />} />
          <Route path="teacher/questions/bank" element={<QuestionBankPage />} />
          <Route path="teacher/groups" element={<TeacherGroupsPage />} />
          <Route path="teacher/results" element={<TeacherResultsPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
