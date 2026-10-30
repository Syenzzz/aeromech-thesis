import os
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))
import figure_review as review


class FigureReviewTests(unittest.TestCase):
    def test_plan_revision_invalidates_confirmation(self):
        with tempfile.TemporaryDirectory() as root:
            review.save_plan(root, [{'figure_id': 'FIG-1', 'title': 'A'}])
            review.confirm_plan(root)
            self.assertTrue(review.plan_confirmed(root))
            review.save_plan(root, [{'figure_id': 'FIG-1', 'title': 'B'}])
            self.assertFalse(review.plan_confirmed(root))

    def test_image_review_tracks_actual_file(self):
        with tempfile.TemporaryDirectory() as root:
            path = os.path.join(root, 'figure.png')
            with open(path, 'wb') as f:
                f.write(b'first')
            review.confirm_image(root, 'FIG-1', path)
            self.assertTrue(review.image_confirmed(root, 'FIG-1', path))
            with open(path, 'wb') as f:
                f.write(b'second')
            self.assertFalse(review.image_confirmed(root, 'FIG-1', path))

    def test_confirmation_is_bound_to_supplied_plan(self):
        with tempfile.TemporaryDirectory() as root:
            figures = [{'figure_id': 'FIG-1', 'title': 'A'}]
            review.save_plan(root, figures)
            review.confirm_plan(root)
            self.assertTrue(review.plan_confirmed(root, figures))
            self.assertFalse(review.plan_confirmed(root, [{'figure_id': 'FIG-1', 'title': 'B'}]))

    def test_unchanged_figure_keeps_confirmation(self):
        with tempfile.TemporaryDirectory() as root:
            figures = [{'figure_id': 'FIG-1', 'title': 'A'},
                       {'figure_id': 'FIG-2', 'title': 'B'}]
            review.save_plan(root, figures)
            review.confirm_plan(root)
            updated = [figures[0], {'figure_id': 'FIG-2', 'title': 'C'}]
            review.save_plan(root, updated)
            self.assertTrue(review.figure_plan_confirmed(root, 'FIG-1', updated))
            self.assertFalse(review.figure_plan_confirmed(root, 'FIG-2', updated))

    def test_project_external_budget_persists_and_fails_closed(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertFalse(review.reserve_external_call(root))
            review.set_external_policy(root, True, 2)
            self.assertTrue(review.reserve_external_call(root))
            self.assertTrue(review.reserve_external_call(root))
            self.assertFalse(review.reserve_external_call(root))
            review.set_external_policy(root, False, 10)
            self.assertFalse(review.reserve_external_call(root))

    def test_external_budget_is_atomic(self):
        with tempfile.TemporaryDirectory() as root:
            review.set_external_policy(root, True, 3)
            with ThreadPoolExecutor(max_workers=8) as pool:
                results = list(pool.map(lambda _: review.reserve_external_call(root), range(12)))
            self.assertEqual(sum(results), 3)

    def test_image_review_requires_current_plan(self):
        with tempfile.TemporaryDirectory() as root:
            figures = [{'figure_id': 'FIG-1', 'title': 'A'}]
            review.save_plan(root, figures)
            review.confirm_plan(root)
            path = os.path.join(root, 'image.png')
            with open(path, 'wb') as f:
                f.write(b'image')
            review.confirm_image(root, 'FIG-1', path)
            self.assertTrue(review.image_ready(root, 'FIG-1', path, figures))
            changed = [{'figure_id': 'FIG-1', 'title': 'B'}]
            review.save_plan(root, changed)
            self.assertFalse(review.image_ready(root, 'FIG-1', path, changed))
            review.confirm_plan(root)
            self.assertFalse(review.image_ready(root, 'FIG-1', path, changed))

    def test_duplicate_ids_cannot_be_confirmed(self):
        with tempfile.TemporaryDirectory() as root:
            review.save_plan(root, [{'figure_id': 'FIG-1'}, {'figure_id': 'FIG-1'}])
            with self.assertRaises(ValueError):
                review.confirm_plan(root)


if __name__ == '__main__':
    unittest.main()
