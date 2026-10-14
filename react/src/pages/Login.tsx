import { AccountPanel, AntiCsrf, BackendRequired, Errors, GlobalErrors, accountBootstrap, accountHref } from "../lib/accountUi";
export default function Login() {
  const b = accountBootstrap();
  return <AccountPanel eyebrow="ACCOUNT" title="Sign in" description="Use the email address associated with your SportsModelHub account.">
    {!b.csrfToken ? <BackendRequired name="Sign in" href="/login.html" /> : <>
      <GlobalErrors data={b} />
      <form method="post" action={window.location.pathname + window.location.search} className="auth-form" noValidate>
        <AntiCsrf token={b.csrfToken} />
        <div className="auth-field"><label htmlFor="auth-email">Email</label><input id="auth-email" type="email" name="username" autoComplete="email" required defaultValue={b.values?.username ?? ""} /><Errors name="username" data={b}/></div>
        <div className="auth-field"><label htmlFor="auth-password">Password</label><input id="auth-password" type="password" name="password" autoComplete="current-password" required /><Errors name="password" data={b}/></div>
        <input type="hidden" name="next" value={b.values?.next ?? new URLSearchParams(window.location.search).get("next") ?? ""} />
        <button type="submit" className="auth-primary">Sign in</button>
      </form>
      <div className="auth-links"><a href={accountHref("/password_reset.html")}>Forgot password?</a><a href={accountHref("/register.html")}>Create account</a></div>
    </>}
  </AccountPanel>;
}