import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))
import figure_iface as fi
import figure_review as review
import thesis_build as build
import thesis_review
import thesis_state


class BuildReviewTests(unittest.TestCase):
    def test_build_requires_explicit_insertion_and_current_image(self):
        with tempfile.TemporaryDirectory() as root:
            os.makedirs(os.path.join(root, '.aeromech'))
            thesis_state.main([root, 'init'])
            state, _ = thesis_state.load_state(root)
            state['research']['plan_file'] = 'plan.md'
            state['research']['outline_file'] = 'outline.md'
            thesis_state.save_state(root, state)
            for name, category in [('plan.md', 'plan'), ('outline.md', 'outline')]:
                with open(os.path.join(root, '.aeromech', name), 'w', encoding='utf-8') as f:
                    f.write(category)
                thesis_review.confirm(root, category, ['.aeromech/' + name])
            with open(os.path.join(root, '.aeromech', 'chapter.md'), 'w', encoding='utf-8') as f:
                f.write('# Chapter\n')
            thesis_review.confirm(root, 'chapters', ['.aeromech/chapter.md'])
            image = os.path.join(root, 'figure.png')
            with open(image, 'wb') as f:
                f.write(b'image')
            plan = [{'figure_id': 'FIG-1', 'name': 'figure'}]
            fi.save_plan(root, plan)
            review.save_plan(root, plan)
            review.confirm_plan(root)
            contract = {'project': {'title': 'Test'}, 'content': {'chapters': ['chapter.md']},
                        'figures': [{'figure_id': 'FIG-1', 'file': 'figure.png'}]}
            self.assertEqual(build.validate_contract(root, contract)['status'], 'ERROR')
            review.confirm_image(root, 'FIG-1', image)
            self.assertEqual(build.validate_contract(root, contract)['status'], 'ERROR')
            review.confirm_insertion(root, 'FIG-1', image, plan)
            self.assertEqual(build.validate_contract(root, contract)['status'], 'PASS')
            with open(image, 'wb') as f:
                f.write(b'changed')
            self.assertEqual(build.validate_contract(root, contract)['status'], 'ERROR')


if __name__ == '__main__':
    unittest.main()
