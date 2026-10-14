import { AccountPanel, AntiCsrf, BackendRequired, Errors, accountBootstrap, accountHref } from "../lib/accountUi";
export default function PasswordReset() {
  const b = accountBootstrap();
  return <AccountPanel eyebrow="SECURITY" title="Reset password" description="Enter your email address. A reset link will be sent if an account exists for that address.">
    {!b.csrfToken ? <BackendRequired name="Password reset" href="/password_reset.html"/> : <form method="post" action={window.location.pathname} className="auth-form" noValidate>
      <AntiCsrf token={b.csrfToken}/><div className="auth-field"><label htmlFor="reset-email">Email</label><input id="reset-email" type="email" name="email" autoComplete="email" required defaultValue={b.values?.email ?? ""}/><Errors data={b} name="email"/></div>
      <button className="auth-primary" type="submit">Send reset link</button>
    </form>}
    <p className="auth-footer"><a href={accountHref("/login.html")}>Back to sign in</a></p>
  </AccountPanel>;
}