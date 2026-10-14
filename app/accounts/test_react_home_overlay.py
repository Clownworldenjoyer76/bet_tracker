"""Source contract and Django route protection for optional historical-picks overlay."""
from pathlib import Path
from django.test import SimpleTestCase, override_settings

PAGE_ROOT=Path(__file__).resolve().parents[2] / 'react' / 'src' / 'pages'

class HomeOverlaySourceContractTests(SimpleTestCase):
    def test_date_cards_have_optional_selection(self):
        source=(PAGE_ROOT / 'BetHistoryDaily.tsx').read_text(encoding='utf-8')
        self.assertIn('onDateSelect?: (day: string, rows: NormalizedRow[]) => void',source)
        self.assertIn('onClick={onDateSelect ?',source)
        self.assertIn('onKeyDown={onDateSelect ?',source)
    def test_home_uses_native_history_and_picks(self):
        source=(PAGE_ROOT / 'Home.tsx').read_text(encoding='utf-8')
        for needle in ('<BetHistoryDaily onDateSelect={openDay} />','selectedDay.rows.map','aria-modal="true"','"Escape"','Close historical picks'):
            self.assertIn(needle,source)
    @override_settings(REACT_HOME_PAGE_ENABLED=False,REACT_ACCOUNT_PAGES_ENABLED=False)
    def test_legacy_home_remains_default(self):
        response=self.client.get('/')
        self.assertEqual(response.status_code,200)
        self.assertNotIn(b'smh-account-bootstrap',response.content)
