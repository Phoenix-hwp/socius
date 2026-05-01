import { NavLink, Outlet } from "react-router-dom";
import styles from "./AppShell.module.css";

export function AppShell() {
  return (
    <div className={styles.root}>
      <aside className={styles.sidebar} aria-label="侧栏导航">
        <div className={styles.brand}>Cursor 工作间</div>
        <nav className={styles.nav}>
          <NavLink end to="/" className={styles.navLink}>
            Notion 作业
          </NavLink>
          <span className={styles.placeholder} title="本期不在范围内">
            网盘同步（占位）
          </span>
          <span className={styles.placeholder} title="本期不在范围内">
            地球图书馆（占位）
          </span>
          <span className={styles.placeholder} title="本期不在范围内">
            项目资料库（占位）
          </span>
        </nav>
      </aside>
      <main className={styles.main}>
        <Outlet />
      </main>
    </div>
  );
}
