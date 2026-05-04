import { Outlet } from "react-router-dom";

import { Header } from "../components/layout/Header/Header";
import { Footer } from "../components/layout/Footer/Footer";
import styles from "./AppLayout.module.css";

export function AppLayout() {
  return (
    <div className={styles.shell}>
      <Header />
      <main className={styles.pageFrame}>
        <Outlet />
      </main>
      <Footer />
    </div>
  );
}
