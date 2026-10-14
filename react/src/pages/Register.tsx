import { AccountPanel, AntiCsrf, BackendRequired, Errors, GlobalErrors, accountBootstrap, accountHref } from "../lib/accountUi";
export default function Register() {
  const b = accountBootstrap();
  return <AccountPanel eyebrow="ACCOUNT" title="Create account" description="Create a SportsModelHub account for your private preferences and personalized features.">
    {!b.csrfToken ? <BackendRequired name="Registration" href="/register.html" /> : <>
      <GlobalErrors data={b}/>
      <form method="post" action={window.location.pathname} className="auth-form" noValidate>
        <AntiCsrf token={b.csrfToken}/>
        <div className="auth-field"><label htmlFor="reg-email">Email</label><input id="reg-email" type="email" name="email" required autoComplete="email" defaultValue={b.values?.email ?? ""}/><Errors name="email" data={b}/></div>
        <div className="auth-field"><label htmlFor="reg-password1">Password</label><input id="reg-password1" type="password" name="password1" required autoComplete="new-password"/><Errors name="password1" data={b}/></div>
        <div className="auth-field"><label htmlFor="reg-password2">Confirm password</label><input id="reg-password2" type="password" name="password2" required autoComplete="new-password"/><Errors name="password2" data={b}/></div>
        <button type="submit" className="auth-primary">Create account</button>
      </form>
      <p className="auth-footer">Already have an account? <a href={accountHref("/login.html")}>Sign in</a></p>
    </>}
  </AccountPanel>;
}