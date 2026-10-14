import { AccountPanel, accountHref } from "../lib/accountUi";
export default function PasswordResetComplete() {
  return <AccountPanel eyebrow="SECURITY" title="Password updated" description="Your password has been changed successfully."><a className="auth-primary auth-button-link" href={accountHref("/login.html")}>Sign in</a></AccountPanel>;
}