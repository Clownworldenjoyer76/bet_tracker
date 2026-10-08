import "./footer.css";

const FOOTER_DISCLAIMER =
  "For informational and entertainment purposes only. Not betting, financial, or legal advice. Data may be delayed or inaccurate; past results don't guarantee future results. Gambling involves risk of loss. Please gamble responsibly.";

const FOOTER_LINKS: ReadonlyArray<{ label: string; href: string }> = [
  { label: "Disclaimer", href: "/disclaimer.html" },
  { label: "Terms", href: "/terms.html" },
  { label: "Privacy", href: "/privacy.html" },
  { label: "Responsible Gambling", href: "/responsible_gambling.html" },
  { label: "Contact", href: "/contact.html" },
];

export default function Footer() {
  return (
    <footer className="smh-footer" role="contentinfo">
      <div className="smh-footer-inner">
        <nav className="smh-footer-links" aria-label="Footer">
          {FOOTER_LINKS.map((link, index) => (
            <span className="smh-footer-item" key={link.href}>
              {index > 0 ? (
                <span className="smh-footer-sep" aria-hidden="true">
                  |
                </span>
              ) : null}
              <a href={link.href}>{link.label}</a>
            </span>
          ))}
        </nav>
        <p className="smh-footer-disclaimer">{FOOTER_DISCLAIMER}</p>
      </div>
    </footer>
  );
}
