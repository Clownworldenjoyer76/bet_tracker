import { AccountPanel, AntiCsrf, BackendRequired, Errors, GlobalErrors, accountBootstrap, accountHref } from "../lib/accountUi";
export default function PasswordResetConfirm() {
  const b = accountBootstrap();
  return <AccountPanel eyebrow="SECURITY" title="Choose a new password">
    {!b.csrfToken ? <BackendRequired name="Password reset confirmation" href="/password_reset.html"/> : b.validLink === false ? <>
      <div role="alert" className="auth-alert auth-alert-error">This reset link is invalid or has already been used.</div>
      <a className="auth-primary auth-button-link" href={accountHref("/password_reset.html")}>Request another link</a>
    </> : <><GlobalErrors data={b}/><form method="post" action={window.location.pathname} className="auth-form" noValidate>
      <AntiCsrf token={b.csrfToken}/>
      <div className="auth-field"><label htmlFor="new-password1">New password</label><input id="new-password1" type="password" name="new_password1" autoComplete="new-password" required/><Errors name="new_password1" data={b}/></div>
      <div className="auth-field"><label htmlFor="new-password2">Confirm new password</label><input id="new-password2" type="password" name="new_password2" autoComplete="new-password" required/><Errors name="new_password2" data={b}/></div>
      <button className="auth-primary" type="submit">Update password</button>
    </form></>}
  </AccountPanel>;
}