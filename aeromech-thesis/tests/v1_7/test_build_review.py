import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))
import figure_iface as fi
import figure_review as review
import thesis_build as build


class BuildReviewTests(unittest.TestCase):
    def test_build_requires_explicit_insertion_and_current_image(self):
        with tempfile.TemporaryDirectory() as root:
            os.makedirs(os.path.join(root, '.aeromech'))
            with open(os.path.join(root, '.aeromech', 'chapter.md'), 'w', encoding='utf-8') as f:
                f.write('# Chapter\n')
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
