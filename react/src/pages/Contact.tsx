import { AccountPanel, AntiCsrf, BackendRequired, Errors, GlobalErrors, accountBootstrap } from "../lib/accountUi";
export default function Contact() {
  const b = accountBootstrap();
  return <AccountPanel eyebrow="SUPPORT" title="Contact / Support">
    {!b.csrfToken ? <BackendRequired name="Contact" href="/contact.html"/> : b.sent ? <p role="status" className="auth-intro">Your message was sent. Replies go to the email address you provided.</p> : <>
      <p className="auth-intro">Send us a message. Replies go to the email address you provide.</p>
      <GlobalErrors data={b}/><form method="post" action={window.location.pathname} className="auth-form" noValidate>
        <AntiCsrf token={b.csrfToken}/>
        <div className="auth-field"><label htmlFor="contact-name">Name</label><input id="contact-name" name="name" required maxLength={100} autoComplete="name" defaultValue={b.values?.name ?? ""}/><Errors name="name" data={b}/></div>
        <div className="auth-field"><label htmlFor="contact-email">Email</label><input id="contact-email" type="email" name="email" required autoComplete="email" defaultValue={b.values?.email ?? ""}/><Errors name="email" data={b}/></div>
        <div className="auth-field"><label htmlFor="contact-subject">Subject</label><input id="contact-subject" name="subject" required maxLength={150} defaultValue={b.values?.subject ?? ""}/><Errors name="subject" data={b}/></div>
        <div className="auth-field"><label htmlFor="contact-message">Message</label><textarea id="contact-message" name="message" required minLength={10} maxLength={5000} rows={7} defaultValue={b.values?.message ?? ""}/><Errors name="message" data={b}/></div>
        <div hidden aria-hidden="true"><label htmlFor="contact-website">Website</label><input id="contact-website" name="website" tabIndex={-1} autoComplete="off"/></div>
        <button type="submit" className="auth-primary">Send message</button>
      </form>
    </>}
  </AccountPanel>;
}