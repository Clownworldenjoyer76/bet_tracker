import { AccountPanel, accountHref } from "../lib/accountUi";
export default function PasswordResetDone() {
  return <AccountPanel eyebrow="SECURITY" title="Check your email" description="If an account exists for that email address, a reset link has been sent."><a className="auth-primary auth-button-link" href={accountHref("/login.html")}>Return to sign in</a></AccountPanel>;
}