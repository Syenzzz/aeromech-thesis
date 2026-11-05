import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))
import thesis_review
import thesis_state
import thesis_build
import stage_routing
import thesis_orchestrator
import figure_iface
import figure_review


class ReviewGateTests(unittest.TestCase):
    def test_review_is_bound_to_file_contents(self):
        with tempfile.TemporaryDirectory() as root:
            path = os.path.join(root, 'plan.md')
            with open(path, 'w', encoding='utf-8') as f:
                f.write('first')
            self.assertFalse(thesis_review.confirmed(root, 'plan', ['plan.md']))
            thesis_review.confirm(root, 'plan', ['plan.md'])
            self.assertTrue(thesis_review.confirmed(root, 'plan', ['plan.md']))
            with open(path, 'w', encoding='utf-8') as f:
                f.write('revised')
            self.assertFalse(thesis_review.confirmed(root, 'plan', ['plan.md']))

    def test_missing_and_outside_files_cannot_be_confirmed(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(ValueError):
                thesis_review.confirm(root, 'plan', ['missing.md'])
            with self.assertRaises(ValueError):
                thesis_review.confirm(root, 'plan', ['../outside.md'])

    def test_malformed_review_state_is_not_confirmation(self):
        with tempfile.TemporaryDirectory() as root:
            os.makedirs(os.path.join(root, '.aeromech'))
            with open(os.path.join(root, 'plan.md'), 'w') as f:
                f.write('plan')
            with open(os.path.join(root, '.aeromech', 'thesis-review.json'), 'w') as f:
                f.write('{"plan": ["invalid"]}')
            self.assertFalse(thesis_review.confirmed(root, 'plan', ['plan.md']))

    def test_chapters_may_be_confirmed_individually(self):
        with tempfile.TemporaryDirectory() as root:
            for name in ('ch1.md', 'ch2.md'):
                with open(os.path.join(root, name), 'w') as f:
                    f.write(name)
            thesis_review.confirm(root, 'chapters', ['ch1.md'])
            self.assertFalse(thesis_review.confirmed(root, 'chapters', ['ch1.md', 'ch2.md']))
            thesis_review.confirm(root, 'chapters', ['ch2.md'])
            self.assertTrue(thesis_review.confirmed(root, 'chapters', ['ch1.md', 'ch2.md']))
            with open(os.path.join(root, 'ch1.md'), 'a') as f:
                f.write(' revised')
            self.assertFalse(thesis_review.confirmed(root, 'chapters', ['ch1.md', 'ch2.md']))
            self.assertTrue(thesis_review.confirmed(root, 'chapters', ['ch2.md']))

    def test_stage_gate_requires_plan_and_outline(self):
        with tempfile.TemporaryDirectory() as root:
            os.makedirs(os.path.join(root, '.aeromech', 'artifacts'))
            for name in ('plan.md', 'outline.md'):
                with open(os.path.join(root, '.aeromech', 'artifacts', name), 'w') as f:
                    f.write(name)
            state = {'research': {'plan_file': 'artifacts/plan.md', 'outline_file': 'artifacts/outline.md'}}
            self.assertTrue(thesis_state.review_gate_problems(state, root, 'S3', 'S5'))
            thesis_review.confirm(root, 'plan', ['.aeromech/artifacts/plan.md'])
            thesis_review.confirm(root, 'outline', ['.aeromech/artifacts/outline.md'])
            self.assertFalse(thesis_state.review_gate_problems(state, root, 'S3', 'S5'))

    def test_transition_and_override_cannot_skip_reviews(self):
        with tempfile.TemporaryDirectory() as root:
            thesis_state.main([root, 'init'])
            state, _ = thesis_state.load_state(root)
            state['stage']['current'] = 'S3'
            state['project']['title'] = 'Topic'
            state['research']['plan_file'] = 'artifacts/plan.md'
            state['research']['outline_file'] = 'artifacts/outline.md'
            thesis_state.save_state(root, state)
            os.makedirs(os.path.join(root, '.aeromech', 'artifacts'), exist_ok=True)
            for name in ('plan.md', 'outline.md'):
                with open(os.path.join(root, '.aeromech', 'artifacts', name), 'w') as f:
                    f.write(name)
            ok, _ = thesis_state.transition(root, 'S5', 'forward')
            self.assertFalse(ok)
            ok, _ = thesis_state.transition(root, 'S5', 'override', override_note='一次完成')
            self.assertFalse(ok)
            thesis_review.confirm(root, 'plan', ['.aeromech/artifacts/plan.md'])
            thesis_review.confirm(root, 'outline', ['.aeromech/artifacts/outline.md'])
            ok, _ = thesis_state.transition(root, 'S5', 'forward')
            self.assertTrue(ok)

    def test_automatic_orchestrator_stops_for_review(self):
        with tempfile.TemporaryDirectory() as root:
            thesis_state.main([root, 'init'])
            state, _ = thesis_state.load_state(root)
            state['stage']['current'] = 'S3'
            state['project']['paper_type'] = 'research'
            thesis_state.save_state(root, state)
            gates = {name: {'status': 'PASS'} for name in ('feasibility', 'agent_loop', 'rqg')}
            with patch.object(stage_routing, 'gates', return_value=(gates, state, {'status': 'OK'})), \
                 patch.object(stage_routing, '_probe', return_value=True), \
                 patch.object(thesis_orchestrator, 'drift_checks', return_value=([], {})):
                route = stage_routing.route(root)
                self.assertEqual(route['next']['action'], 'human_review')
                rc, result = thesis_orchestrator.step(root)
                self.assertNotEqual(rc, 0)
                self.assertEqual(result['action'], 'NEEDS_HUMAN_REVIEW')

    def test_figure_review_required_even_without_legacy_review_file(self):
        with tempfile.TemporaryDirectory() as root:
            figure = {'figure_id': 'FIG-1', 'kind': 'user_asset', 'out': 'figure.png'}
            figure_iface.save_plan(root, [figure])
            with open(os.path.join(root, 'figure.png'), 'wb') as f:
                f.write(b'image')
            figure_iface.record(root, 'FIG-1', 'GENERATED', artifact='figure.png')
            self.assertTrue(any('配图 FIG-1' in p for p in thesis_state.review_gate_problems({}, root, 'S8', 'S9')))
            figure_review.save_plan(root, [figure])
            figure_review.confirm_plan(root)
            figure_review.confirm_image(root, 'FIG-1', os.path.join(root, 'figure.png'))
            self.assertFalse(any('配图 FIG-1' in p for p in thesis_state.review_gate_problems({}, root, 'S8', 'S9')))
            with open(os.path.join(root, 'figure.png'), 'ab') as f:
                f.write(b'changed')
            self.assertTrue(any('配图 FIG-1' in p for p in thesis_state.review_gate_problems({}, root, 'S8', 'S9')))

    def test_corrupt_figure_review_fails_closed(self):
        with tempfile.TemporaryDirectory() as root:
            figure = {'figure_id': 'FIG-1', 'kind': 'user_asset', 'out': 'figure.png'}
            figure_iface.save_plan(root, [figure])
            folder = os.path.join(root, '.aeromech', 'figures')
            with open(os.path.join(folder, 'review.json'), 'w', encoding='utf-8') as f:
                f.write('{broken')
            result = figure_iface.generate_figure(root, 'FIG-1')
            self.assertEqual(result['status'], 'NEEDS_HUMAN_REVIEW')
            self.assertTrue(any('配图' in p for p in thesis_state.review_gate_problems({}, root, 'S8', 'S9')))

    def test_empty_figure_plan_requires_explicit_confirmation(self):
        with tempfile.TemporaryDirectory() as root:
            figure_iface.save_plan(root, [])
            self.assertTrue(any('配图' in p for p in thesis_state.review_gate_problems({}, root, 'S8', 'S9')))
            figure_review.save_plan(root, [])
            figure_review.confirm_plan(root)
            self.assertFalse(any('配图' in p for p in thesis_state.review_gate_problems({}, root, 'S8', 'S9')))

    def test_corrupt_figure_plan_blocks_advance(self):
        with tempfile.TemporaryDirectory() as root:
            os.makedirs(os.path.join(root, '.aeromech', 'figures'))
            with open(figure_iface.plan_path(root), 'w') as f:
                f.write('figures: [broken')
            self.assertTrue(any('配图' in p for p in thesis_state.review_gate_problems({}, root, 'S8', 'S9')))

    def test_chapter_gate_rejects_missing_or_changed_chapter(self):
        with tempfile.TemporaryDirectory() as root:
            folder = os.path.join(root, '.aeromech', 'artifacts', 'chapters')
            os.makedirs(folder)
            path = os.path.join(folder, 'ch1.md')
            with open(path, 'w') as f:
                f.write('chapter')
            self.assertTrue(any('章节' in p for p in thesis_state.review_gate_problems({}, root, 'S7', 'S8')))
            thesis_review.confirm(root, 'chapters', ['.aeromech/artifacts/chapters/ch1.md'])
            self.assertFalse(any('章节' in p for p in thesis_state.review_gate_problems({}, root, 'S7', 'S8')))
            with open(path, 'a') as f:
                f.write(' revised')
            self.assertTrue(any('章节' in p for p in thesis_state.review_gate_problems({}, root, 'S7', 'S8')))

    def test_build_without_review_is_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            os.makedirs(os.path.join(root, '.aeromech'))
            with open(os.path.join(root, '.aeromech', 'chapter.md'), 'w', encoding='utf-8') as f:
                f.write('# Chapter')
            contract = {'project': {'title': 'Test'}, 'content': {'chapters': ['chapter.md']}}
            result = thesis_build.validate_contract(root, contract)
            self.assertEqual(result['status'], 'ERROR')
            self.assertTrue(any('章节' in e and '确认' in e for e in result['errors']))
            thesis_review.confirm(root, 'chapters', ['.aeromech/chapter.md'])
            self.assertEqual(thesis_build.validate_contract(root, contract)['status'], 'ERROR')


if __name__ == '__main__':
    unittest.main()
