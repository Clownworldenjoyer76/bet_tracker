import InfoPageLayout from "../components/InfoPageLayout";

export default function Privacy() {
  return (
    <InfoPageLayout title="Privacy Policy — Draft">
      <section><h2>Review required</h2><p>This draft is not an approved privacy policy. Publication requires confirmation of data collected, data retention, cookies and analytics, billing processors, user rights, and a contact address.</p></section>
      <section><h2>Account information</h2><p>The service supports user accounts and may store preferences associated with an authenticated user. Confirm the complete data inventory with the site operator before publishing.</p></section>
      <section><h2>Support messages</h2><p>Contact forms receive information supplied by the sender. Confirm handling, retention, and access controls before this page replaces the existing policy.</p></section>
      <p><a href="/contact.html">Contact / Support</a></p>
    </InfoPageLayout>
  );
}
