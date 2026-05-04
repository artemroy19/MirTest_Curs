import { useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { useSessionStore } from "../../../store/sessionStore";
import { getDefaultRoute } from "../../../utils/routes";
import headerStyles from "./Header.module.css";

const teacherMenuItems = [
  { label: "Мои тесты", path: "/teacher/tests" },
  { label: "Банк вопросов", path: "/teacher/questions/bank" },
  { label: "Группы", path: "/teacher/groups" },
  { label: "Результаты", path: "/teacher/results" },
  { label: "Профиль", path: "/profile" }
];

const studentMenuItems = [
  { label: "Мои тесты", path: "/tests" },
  { label: "Мои группы", path: "/groups" },
  { label: "Результаты", path: "/results" },
  { label: "Профиль", path: "/profile" }
];

function getNavigation(role?: string) {
  if (role === "teacher" || role === "admin") {
    return teacherMenuItems;
  }
  return studentMenuItems;
}

export function Header() {
  const navigate = useNavigate();
  const user = useSessionStore((s) => s.user);
  const clearSession = useSessionStore((s) => s.clearSession);
  const [navOpen, setNavOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const navItems = getNavigation(user?.role);
  const homePath = getDefaultRoute(user?.role);

  function handleLogout() {
    clearSession();
    navigate("/login");
  }

  return (
    <header className={headerStyles.header}>
      <div className={headerStyles.leftGroup}>
        <button type="button" className={headerStyles.burger} onClick={() => setNavOpen((open) => !open)}>
          <span />
          <span />
          <span />
        </button>
        <NavLink to={homePath} className={headerStyles.logo}>
          MirTest
        </NavLink>
        <nav className={headerStyles.desktopNav}>
          {navItems.map((item) => (
            <NavLink key={item.path} to={item.path} className={({ isActive }) => `${headerStyles.link} ${isActive ? headerStyles.active : ""}`}>
              {item.label}
            </NavLink>
          ))}
        </nav>
      </div>

      <div className={headerStyles.rightGroup}>
        <button type="button" className={headerStyles.profileButton} onClick={() => setProfileOpen((open) => !open)}>
          {user?.avatar ? (
            <img src={user.avatar} alt="Avatar" className={headerStyles.avatar} />
          ) : (
            <div className={headerStyles.avatarPlaceholder}>
              {user?.first_name?.[0]}{user?.last_name?.[0]}
            </div>
          )}
        </button>

        {profileOpen && (
          <div className={headerStyles.profileMenu}>
            <button type="button" className={headerStyles.logoutButton} onClick={handleLogout}>
              Выйти
            </button>
          </div>
        )}
      </div>

      {navOpen && (
        <div className={headerStyles.mobileNavPanel}>
          <nav className={headerStyles.mobileNav}>
            {navItems.map((item) => (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) => `${headerStyles.mobileNavLink} ${isActive ? headerStyles.active : ""}`}
                onClick={() => setNavOpen(false)}
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
        </div>
      )}
    </header>
  );
}
