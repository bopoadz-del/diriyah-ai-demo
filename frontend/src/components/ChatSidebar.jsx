import React, { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { NavLink } from "react-router-dom";
import LanguageSwitcher from "./LanguageSwitcher";

function SidebarIcon({ type }) {
  let paths;

  switch (type) {
    case "notifications":
      paths = (
        <>
          <path d="M18 15v-5a6 6 0 0 0-12 0v5" />
          <path d="M5 15h14" />
          <path d="M9 19a3 3 0 0 0 6 0" />
        </>
      );
      break;
    case "settings":
      paths = (
        <>
          <path d="M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z" />
          <path
            d="M19.4 12a7.4 7.4 0 0 0-.1-1l2.1-1.6-2-3.4-2.5 1a7.5 7.5 0 0 0-1.7-1l-.3-2.7h-4l-.3 2.7a7.5 7.5 0 0 0-1.7 1l-2.5-1-2 3.4 2.1 1.6a7.4 7.4 0 0 0-.1 1 7.4 7.4 0 0 0 .1 1l-2.1 1.6 2 3.4 2.5-1a7.5 7.5 0 0 0 1.7 1l.3 2.7h4l.3-2.7a7.5 7.5 0 0 0 1.7-1l2.5 1 2-3.4-2.1-1.6a7.4 7.4 0 0 0 .1-1z"
          />
        </>
      );
      break;
    default:
      paths = null;
  }

  return (
    <svg
      className="icon__svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      role="presentation"
      aria-hidden="true"
    >
      {paths}
    </svg>
  );
}

function formatGroupState(groups) {
  return groups.reduce((accumulator, group) => {
    accumulator[group.id] = Boolean(group.defaultCollapsed);
    return accumulator;
  }, {});
}

export default function Sidebar({
  projects,
  activeProjectId,
  onProjectChange,
  chatGroups,
  activeChatId,
  onChatSelect,
  onCreateChat,
}) {
  const { t } = useTranslation();
  const [collapsedGroups, setCollapsedGroups] = useState(() => formatGroupState(chatGroups));

  const activeProject = useMemo(
    () => projects.find((project) => project.id === activeProjectId),
    [projects, activeProjectId],
  );

  const handleGroupToggle = (groupId) => {
    setCollapsedGroups((previous) => ({
      ...previous,
      [groupId]: !previous[groupId],
    }));
  };

  const handleProjectChange = (event) => {
    onProjectChange(event.target.value);
  };

  return (
    <aside className="sidebar" aria-label={t("sidebar.navigator")}>
      <section className="sidebar__section" aria-label={t("sidebar.createChat")}>
        <div className="sidebar__logo">Diriyah Brain</div>
        <p className="sidebar__tagline">{t("sidebar.tagline")}</p>
        <button type="button" className="sidebar__new-chat" onClick={onCreateChat}>
          {t("sidebar.newChat")}
        </button>
        <LanguageSwitcher />
      </section>

      <section className="sidebar__section" aria-label="Workspace navigation">
        <p className="sidebar__label">Workspace views</p>
        <nav className="sidebar__nav">
          <NavLink to="/dashboard" className={({ isActive }) => `sidebar__nav-link ${isActive ? "is-active" : ""}`}>
            Dashboard
          </NavLink>
          <NavLink to="/chat" className={({ isActive }) => `sidebar__nav-link ${isActive ? "is-active" : ""}`}>
            Chat
          </NavLink>
          <NavLink to="/analytics" className={({ isActive }) => `sidebar__nav-link ${isActive ? "is-active" : ""}`}>
            Analytics
          </NavLink>
          <NavLink to="/progress" className={({ isActive }) => `sidebar__nav-link ${isActive ? "is-active" : ""}`}>
            Progress
          </NavLink>
          <NavLink to="/files" className={({ isActive }) => `sidebar__nav-link ${isActive ? "is-active" : ""}`}>
            Files
          </NavLink>
          <NavLink to="/settings" className={({ isActive }) => `sidebar__nav-link ${isActive ? "is-active" : ""}`}>
            Settings
          </NavLink>
        </nav>
      </section>

      <section className="sidebar__section" aria-label={t("sidebar.activeProject")}>
        <label htmlFor="project-select" className="sidebar__label">
          {t("sidebar.activeProject")}
        </label>
        <select
          id="project-select"
          className="sidebar__dropdown"
          value={activeProjectId}
          onChange={handleProjectChange}
        >
          {projects.map((project) => (
            <option key={project.id} value={project.id}>
              {project.name}
            </option>
          ))}
        </select>
        {activeProject ? (
          <p className="sidebar__project-meta">
            {activeProject.location} • {activeProject.phase}
          </p>
        ) : null}
      </section>

      <nav className="sidebar__chats" aria-label={t("sidebar.history")}>
        {chatGroups.map((group) => {
          const collapsed = collapsedGroups[group.id];
          return (
            <div key={group.id} className="sidebar__group">
              <button
                type="button"
                className="sidebar__group-toggle"
                onClick={() => handleGroupToggle(group.id)}
                aria-expanded={!collapsed}
                aria-controls={`${group.id}-list`}
              >
                <span>{group.label}</span>
                <span className="sidebar__group-caret" aria-hidden>{collapsed ? "▸" : "▾"}</span>
              </button>
              <ul
                id={`${group.id}-list`}
                className={`sidebar__chat-list ${collapsed ? "sidebar__chat-list--collapsed" : ""}`}
              >
                {group.chats.map((chat) => {
                  const isActive = chat.id === activeChatId;
                  return (
                    <li key={chat.id}>
                      <button
                        type="button"
                        className={`sidebar__chat-button ${isActive ? "sidebar__chat-button--active" : ""}`}
                        onClick={() => onChatSelect(chat.id)}
                        aria-pressed={isActive}
                      >
                        <div className="sidebar__chat-header">
                          <span className="sidebar__chat-title">{chat.title}</span>
                          <span className="sidebar__chat-time">{chat.timestamp}</span>
                        </div>
                        <p className="sidebar__chat-preview">{chat.preview}</p>
                        {chat.unread ? (
                          <span className="sidebar__chat-unread" aria-label={`${chat.unread} unread messages`}>
                            {chat.unread}
                          </span>
                        ) : null}
                        {chat.isDraft ? <span className="sidebar__chat-draft">{t("sidebar.draft")}</span> : null}
                      </button>
                    </li>
                  );
                })}
              </ul>
            </div>
          );
        })}
      </nav>

      <footer className="sidebar__bottom">
        <div className="sidebar__profile" aria-label={t("sidebar.profile.role")}>
          <div className="sidebar__avatar" aria-hidden>
            KM
          </div>
          <div>
            <p className="sidebar__profile-name">{t("sidebar.profile.name")}</p>
            <p className="sidebar__profile-role">{t("sidebar.profile.role")}</p>
          </div>
        </div>
        <div className="sidebar__actions" aria-label="Sidebar quick actions">
          <button type="button" className="sidebar__icon" title={t("sidebar.notifications")}>
            <SidebarIcon type="notifications" />
          </button>
          <button type="button" className="sidebar__icon" title={t("sidebar.settings")}>
            <SidebarIcon type="settings" />
          </button>
        </div>
      </footer>
    </aside>
  );
}
