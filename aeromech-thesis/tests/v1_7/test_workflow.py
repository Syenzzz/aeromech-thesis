import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))
import figure_iface as FI
import figure_review as review
import figure_workflow as workflow
import image_provider
import ai_figure_gate
import image_backends


class WorkflowTests(unittest.TestCase):
    def test_fault_tree_rejects_missing_semantics(self):
        with tempfile.TemporaryDirectory() as root:
            import json
            with open(os.path.join(root, 'source.json'), 'w', encoding='utf-8') as f:
                json.dump({'nodes': [{'id': 'a', 'text': 'Fault', 'x': 1, 'y': 1, 'w': 3, 'h': 1}]}, f)
            spec = {'figure_id': 'FIG-1', 'type': 'fault_tree', 'kind': 'editable',
                    'source': 'source.json', 'out': 'figure.png'}
            FI.save_plan(root, [spec])
            review.save_plan(root, [spec])
            review.confirm_plan(root)
            self.assertEqual(FI.generate_figure(root, 'FIG-1')['status'], 'REJECTED')

    def test_fault_tree_with_explicit_gate_and_events(self):
        with tempfile.TemporaryDirectory() as root:
            import json
            nodes = [{'id': 'top', 'text': 'Top', 'semantic': 'top_event', 'x': 3, 'y': 1, 'w': 3, 'h': 1},
                     {'id': 'gate', 'text': 'OR门', 'semantic': 'gate', 'x': 3, 'y': 3, 'w': 3, 'h': 1},
                     {'id': 'a', 'text': 'A', 'semantic': 'basic_event', 'x': 1, 'y': 5, 'w': 3, 'h': 1},
                     {'id': 'b', 'text': 'B', 'semantic': 'basic_event', 'x': 5, 'y': 5, 'w': 3, 'h': 1}]
            edges = [{'from': 'top', 'to': 'gate'}, {'from': 'gate', 'to': 'a'}, {'from': 'gate', 'to': 'b'}]
            with open(os.path.join(root, 'source.json'), 'w', encoding='utf-8') as f:
                json.dump({'nodes': nodes, 'edges': edges}, f)
            spec = {'figure_id': 'FIG-1', 'type': 'fault_tree', 'kind': 'editable',
                    'source': 'source.json', 'out': 'figure.png'}
            FI.save_plan(root, [spec])
            review.save_plan(root, [spec])
            review.confirm_plan(root)
            self.assertEqual(FI.generate_figure(root, 'FIG-1')['status'], 'GENERATED')
            with open(os.path.join(root, 'figure.layout.json'), encoding='utf-8') as f:
                self.assertIn('gate', {node['role'] for node in json.load(f)['boxes']})

    def test_existing_image_can_be_registered_after_plan_confirmation(self):
        with tempfile.TemporaryDirectory() as root:
            with open(os.path.join(root, 'old.png'), 'wb') as f:
                f.write(b'old image')
            spec = {'figure_id': 'FIG-OLD', 'out': 'old.png', 'kind': 'user_asset'}
            FI.save_plan(root, [spec])
            workflow.main([root, 'sync-plan'])
            self.assertEqual(workflow.main([root, 'adopt-existing', '--figure', 'FIG-OLD']), 1)
            workflow.main([root, 'confirm-plan'])
            self.assertEqual(workflow.main([root, 'adopt-existing', '--figure', 'FIG-OLD']), 0)
            self.assertEqual(workflow.main([root, 'confirm-image', '--figure', 'FIG-OLD']), 0)

    def test_cli_rejects_generation_before_workflow_is_enabled(self):
        with tempfile.TemporaryDirectory() as root:
            fi = FI.main([root, 'generate', '--figure', 'FIG-1'])
            self.assertEqual(fi, 1)

    def test_external_budget_blocks_backend(self):
        with tempfile.TemporaryDirectory() as root:
            spec = {'figure_id': 'FIG-1', 'provider': 'external', 'out': 'image.png'}
            FI.save_plan(root, [spec])
            review.save_plan(root, [spec])
            review.confirm_plan(root)
            decision = {'provider': 'external_image', 'needs_configuration': False,
                        'external_backend': 'openai', 'external_model': 'test',
                        'credential': 'unused'}
            with patch.object(image_provider, 'route', return_value=decision), \
                 patch.object(ai_figure_gate, 'plan_gate', return_value=(True, {})), \
                 patch.object(ai_figure_gate, 'assemble_prompt', return_value=('prompt', 'hash')), \
                 patch.object(ai_figure_gate, 'build_provenance', return_value=({}, [])), \
                 patch.object(image_backends, 'get_backend') as backend:
                result = FI.generate_figure(root, 'FIG-1')
                self.assertEqual(result['reason'], 'EXTERNAL_AUTHORIZATION_OR_BUDGET_REQUIRED')
                backend.return_value.generate.assert_not_called()
                review.set_external_policy(root, True, 1)
                def generate(_prompt, out_path):
                    with open(out_path, 'wb') as f:
                        f.write(b'image')
                backend.return_value.generate.side_effect = generate
                self.assertEqual(FI.generate_figure(root, 'FIG-1')['status'], 'GENERATED')
                self.assertEqual(FI.generate_figure(root, 'FIG-1')['reason'], 'EXTERNAL_AUTHORIZATION_OR_BUDGET_REQUIRED')
                self.assertEqual(backend.return_value.generate.call_count, 1)

    def test_editable_generation_requires_confirmed_plan(self):
        with tempfile.TemporaryDirectory() as root:
            import json
            with open(os.path.join(root, 'source.json'), 'w', encoding='utf-8') as f:
                json.dump({'nodes': [{'id': 'a', 'text': 'Step', 'x': 1, 'y': 1, 'w': 3, 'h': 1}]}, f)
            spec = {'figure_id': 'FIG-1', 'kind': 'editable', 'source': 'source.json', 'out': 'figure.png'}
            FI.save_plan(root, [spec])
            review.save_plan(root, [spec])
            self.assertEqual(FI.generate_figure(root, 'FIG-1')['reason'], 'PLAN_CONFIRMATION_REQUIRED')
            review.confirm_plan(root)
            self.assertEqual(FI.generate_figure(root, 'FIG-1')['status'], 'GENERATED')
            self.assertTrue(os.path.isfile(os.path.join(root, 'figure.pptx')))
            image = os.path.join(root, 'figure.png')
            review.confirm_image(root, 'FIG-1', image)
            self.assertTrue(review.image_confirmed(root, 'FIG-1', image))
            with open(os.path.join(root, 'figure.pptx'), 'ab') as f:
                f.write(b'changed')
            self.assertFalse(review.image_confirmed(root, 'FIG-1', image))
            with open(os.path.join(root, 'source.json'), 'w', encoding='utf-8') as f:
                json.dump({'nodes': []}, f)
            self.assertEqual(FI.generate_figure(root, 'FIG-1')['reason'], 'PLAN_CONFIRMATION_REQUIRED')

    def test_plan_confirmation_and_changed_image(self):
        with tempfile.TemporaryDirectory() as root:
            spec = {'figure_id': 'FIG-1', 'name': 'test', 'kind': 'none'}
            FI.save_plan(root, [spec])
            self.assertEqual(workflow.main([root, 'sync-plan']), 0)
            self.assertEqual(workflow.main([root, 'confirm-plan']), 0)
            image = os.path.join(root, 'image.png')
            with open(image, 'wb') as out:
                out.write(b'image')
            FI.record(root, 'FIG-1', 'GENERATED', artifact='image.png', provider='test')
            self.assertEqual(workflow.main([root, 'confirm-image', '--figure', 'FIG-1']), 0)
            self.assertTrue(review.image_ready(root, 'FIG-1', image, [spec]))
            self.assertFalse(review.insertion_ready(root, 'FIG-1', image, [spec]))
            review.confirm_insertion(root, 'FIG-1', image, [spec])
            self.assertTrue(review.insertion_ready(root, 'FIG-1', image, [spec]))
            with open(image, 'wb') as out:
                out.write(b'changed')
            self.assertFalse(review.image_ready(root, 'FIG-1', image, [spec]))
            self.assertEqual(workflow.main([root, 'confirm-image', '--figure', 'FIG-1']), 1)


if __name__ == '__main__':
    unittest.main()
