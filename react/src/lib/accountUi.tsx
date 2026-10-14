import type { ReactNode } from "react";
import "../../../app/frontend/src/assets/css/pages/auth.css";

export const ACCOUNT_ORIGIN = "https://api.sportsmodelhub.com";
export type Message = {
  subject: string; message: string; created: string; replied: boolean;
  reply?: string; repliedAt?: string;
};
export type AccountBootstrap = {
  page?: string;
  authenticated?: boolean;
  csrfToken?: string;
  values?: Record<string, string>;
  errors?: Record<string, string[]>;
  nonFieldErrors?: string[];
  validLink?: boolean;
  sent?: boolean;
  profile?: {
    email?: string; joined?: string; plan?: string; status?: string;
    features?: string[]; messages?: Message[];
    timezone?: string; bankroll?: string; kellyFraction?: string;
    timezoneOptions?: Array<{ value: string; label: string }>;
    billingCheckoutConfigured?: boolean; billingCustomerLinked?: boolean;
    billingExternalStatus?: string; billingNotice?: string;
  };
};

export function accountBootstrap(): AccountBootstrap {
  const node = document.getElementById("smh-account-bootstrap");
  if (!node?.textContent) return {};
  try {
    const parsed: unknown = JSON.parse(node.textContent);
    if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) return parsed as AccountBootstrap;
  } catch { /* unavailable or untrusted bootstrap: fail closed */ }
  return {};
}
export function accountHref(path: string): string {
  const canonical = path.startsWith("/") ? path : `/${path}`;
  if (window.location.hostname === "bt.sportsmodelhub.com") return ACCOUNT_ORIGIN + canonical;
  return canonical;
}
export function AntiCsrf({ token }: { token?: string }) {
  return <input type="hidden" name="csrfmiddlewaretoken" value={token ?? ""} />;
}
export function Errors({ name, data }: { name: string; data: AccountBootstrap }) {
  return <>{(data.errors?.[name] ?? []).map((e, i) => <div role="alert" className="auth-field-error" key={`${name}-${i}`}>{e}</div>)}</>;
}
export function GlobalErrors({ data }: { data: AccountBootstrap }) {
  return <>{(data.nonFieldErrors ?? []).map((e, i) => <div role="alert" className="auth-alert auth-alert-error" key={i}>{e}</div>)}</>;
}
export function AccountPanel({ eyebrow, title, description, children }: {
  eyebrow: string; title: string; description?: string; children: ReactNode;
}) {
  return <main className="auth-page"><section className="auth-shell">
    <div className="auth-card auth-card-wide">
      <div className="auth-eyebrow">{eyebrow}</div>
      <h1>{title}</h1>
      {description ? <p className="auth-intro">{description}</p> : null}
      {children}
    </div>
  </section></main>;
}
export function BackendRequired({ name, href }: { name: string; href: string }) {
  return <p className="auth-intro">{name} requires the secure Django account server. <a href={ACCOUNT_ORIGIN + href}>Open the account page</a>.</p>;
}