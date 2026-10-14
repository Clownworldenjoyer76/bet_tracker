import { AccountPanel, AntiCsrf, BackendRequired, Errors, GlobalErrors, accountBootstrap, accountHref } from "../lib/accountUi";
export default function Account() {
  const b = accountBootstrap();
  const p = b.profile;
  return <AccountPanel eyebrow="ACCOUNT" title="Your account" description="Private account information and preferences are attached to your authenticated user record.">
    {!b.authenticated || !p || !b.csrfToken ? <BackendRequired name="Account" href="/account.html"/> : <>
      <dl className="account-details">
        <div><dt>Email</dt><dd>{p.email ?? "—"}</dd></div>
        <div><dt>Joined</dt><dd>{p.joined ?? "—"}</dd></div>
        <div><dt>Plan</dt><dd>{p.plan ?? "—"}</dd></div>
        <div><dt>Subscription</dt><dd>{p.status ?? "—"}</dd></div>
      </dl>
      <section className="account-section" id="inbox"><div className="auth-eyebrow">INBOX</div><h2>Messages</h2>
        {(p.messages ?? []).length === 0 ? <p className="auth-intro">No messages yet.</p> : <ul className="smh-inbox">{(p.messages ?? []).map((m, i) => <li className="smh-inbox-item" key={i}>
          <strong>{m.subject}</strong><p className="auth-help">{m.created} · {m.replied ? "Replied" : "Awaiting reply"}</p><p>{m.message}</p>
          {m.reply ? <section><p className="auth-help">Reply from SportsModelHub · {m.repliedAt}</p><p>{m.reply}</p></section> : null}
        </li>)}</ul>}
        <p className="auth-help"><a href={accountHref("/contact.html")}>Contact support</a></p>
      </section>
      <section className="account-section"><div className="auth-eyebrow">ACCESS</div><h2>Entitlements</h2>
        <div className="account-feature-list">{(p.features ?? []).length ? p.features?.map(f => <span className="account-feature" key={f}>{f}</span>) : <span className="auth-help">No active feature entitlements.</span>}</div>
      </section>
      <section className="account-section"><div className="auth-eyebrow">BILLING</div><h2>Subscription billing</h2>
        {p.billingNotice === "success" ? <p role="status">Checkout completed. Access updates after Stripe confirms the webhook.</p> : null}
        {p.billingNotice === "canceled" ? <p>Checkout canceled; your plan is unchanged.</p> : null}
        {p.billingExternalStatus ? <p>Provider status: {p.billingExternalStatus}</p> : null}
        {p.billingCheckoutConfigured && p.plan?.toLowerCase() === "free" ? <form method="post" action="/billing/checkout/"><AntiCsrf token={b.csrfToken}/><button type="submit" className="auth-primary">Upgrade to Pro</button></form> : null}
        {p.billingCustomerLinked ? <form method="post" action="/billing/portal/"><AntiCsrf token={b.csrfToken}/><button type="submit" className="auth-secondary">Manage billing</button></form> : null}
        {!p.billingCheckoutConfigured ? <p className="auth-intro">Subscription checkout is not configured.</p> : null}
      </section>
      <section className="account-section"><div className="auth-eyebrow">PREFERENCES</div><h2>Display &amp; Kelly settings</h2><GlobalErrors data={b}/>
        <form method="post" action="/account.html" className="auth-form" noValidate><AntiCsrf token={b.csrfToken}/>
          <div className="auth-field"><label htmlFor="pref-zone">Timezone</label><select id="pref-zone" name="timezone" defaultValue={b.values?.timezone ?? p.timezone ?? ""}>{(p.timezoneOptions ?? []).map(z => <option value={z.value} key={z.value}>{z.label}</option>)}</select><Errors name="timezone" data={b}/></div>
          <div className="auth-field"><label htmlFor="pref-bankroll">Bankroll</label><input id="pref-bankroll" type="number" name="bankroll" min="0" step="0.01" inputMode="decimal" defaultValue={b.values?.bankroll ?? p.bankroll ?? ""}/><Errors name="bankroll" data={b}/></div>
          <div className="auth-field"><label htmlFor="pref-kelly">Kelly fraction</label><select id="pref-kelly" name="kelly_fraction" defaultValue={b.values?.kelly_fraction ?? p.kellyFraction ?? "1.00"}><option value="1.00">Full</option><option value="0.50">Half</option><option value="0.25">Quarter</option></select><Errors name="kelly_fraction" data={b}/></div>
          <button type="submit" className="auth-primary">Save preferences</button>
        </form>
      </section>
      <section className="account-section account-section-last"><form method="post" action="/logout.html"><AntiCsrf token={b.csrfToken}/><button type="submit" className="auth-secondary">Sign out</button></form></section>
    </>}
  </AccountPanel>;
}