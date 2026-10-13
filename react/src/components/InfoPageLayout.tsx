import type { ReactNode } from "react";
import "../../../app/frontend/src/assets/css/pages/info.css";

type Props = { title: string; eyebrow?: string; children: ReactNode };
export default function InfoPageLayout({ title, eyebrow, children }: Props) {
  return (
    <main className="info-page">
      {eyebrow ? <p className="auth-eyebrow">{eyebrow}</p> : null}
      <h1 className="info-title">{title}</h1>
      <div className="info-content">{children}</div>
    </main>
  );
}
