import { useState } from "react";
import toolCheatSheets, { type CheatSheet } from "../../data/toolCheatSheets";
import styles from "./ToolCheatSheet.module.css";

interface ToolCheatSheetProps {
  activeToolId: string;
}

export function ToolCheatSheet({ activeToolId }: ToolCheatSheetProps) {
  const [isOpen, setIsOpen] = useState(false);

  const sheet: CheatSheet | undefined = toolCheatSheets[activeToolId];

  if (!sheet) return null;

  return (
    <aside
      className={`${styles.panel} ${isOpen ? styles.panelOpen : styles.panelClosed}`}
      aria-label="Learning Center"
    >
      <button
        type="button"
        className={styles.trigger}
        aria-expanded={isOpen ? "true" : "false"}
        aria-controls="learning-panel-content"
        aria-label="Learning Center"
        onClick={() => setIsOpen((prev) => !prev)}
      >
        <span className={styles.triggerIcon} aria-hidden="true">
          {isOpen ? "✕" : "?"}
        </span>
        {!isOpen && <span className={styles.triggerLabel}>Learning Center</span>}
      </button>

      {isOpen && (
        <div
          id="learning-panel-content"
          className={styles.content}
          data-testid="learning-panel-content"
        >
          <header className={styles.header}>
            <h2 className={styles.heading}>{sheet.toolName} Quick Reference</h2>
          </header>

          <section className={styles.section} aria-labelledby="lc-overview">
            <h3 id="lc-overview" className={styles.sectionHeading}>What it does</h3>
            <p className={styles.body}>{sheet.overview}</p>
          </section>

          <section className={styles.section} aria-labelledby="lc-flags">
            <h3 id="lc-flags" className={styles.sectionHeading}>Common Flags</h3>
            <dl className={styles.flagList}>
              {sheet.flags.map(({ flag, description }) => (
                <div key={flag} className={styles.flagRow}>
                  <dt className={styles.flagCode}>{flag}</dt>
                  <dd className={styles.flagDesc}>{description}</dd>
                </div>
              ))}
            </dl>
          </section>

          <section className={styles.section} aria-labelledby="lc-tip">
            <h3 id="lc-tip" className={styles.sectionHeading}>Ethical Hacking Tip</h3>
            <p className={`${styles.body} ${styles.tipBody}`}>⚠ {sheet.ethicalTip}</p>
          </section>
        </div>
      )}
    </aside>
  );
}

export default ToolCheatSheet;
