import os
import sys
import tempfile
import unittest
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))
import editable_figure
from pptx import Presentation


class EditableFigureTests(unittest.TestCase):
    def test_diagram_outputs_editable_shapes_and_vector(self):
        spec = {'nodes': [{'id': 'a', 'text': 'Start', 'x': 1, 'y': 1, 'w': 3, 'h': 1},
                          {'id': 'b', 'text': 'Finish', 'x': 1, 'y': 3, 'w': 3, 'h': 1}],
                'edges': [{'from': 'a', 'to': 'b'}]}
        with tempfile.TemporaryDirectory() as root:
            files = editable_figure.render(spec, os.path.join(root, 'figure'))
            self.assertTrue(all(os.path.isfile(p) for p in files.values()))
            shapes = Presentation(files['pptx']).slides[0].shapes
            self.assertGreaterEqual(len(shapes), 3)
            self.assertEqual([s.text for s in shapes if s.has_text_frame], ['Start', 'Finish'])
            self.assertEqual(str(shapes[0].text_frame.paragraphs[0].font.color.rgb), '1F2933')
            with open(files['layout'], encoding='utf-8') as f:
                layout = json.load(f)
            self.assertEqual(len(layout['boxes']), 2)
            self.assertEqual(len(layout['edges']), 1)
            self.assertEqual(len(layout['texts']), 2)

    def test_missing_edge_target_fails(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(ValueError):
                editable_figure.render({'nodes': [], 'edges': [{'from': 'a', 'to': 'b'}]}, os.path.join(root, 'f'))

    def test_decision_and_edge_label_are_editable(self):
        spec = {'nodes': [{'id': 'a', 'text': 'Decision', 'x': 1, 'y': 1, 'w': 3, 'h': 2, 'shape': 'diamond'},
                          {'id': 'b', 'text': 'High risk', 'x': 1, 'y': 4, 'w': 4, 'h': 2, 'role': 'high'}],
                'edges': [{'from': 'a', 'to': 'b', 'label': 'Yes'}]}
        with tempfile.TemporaryDirectory() as root:
            files = editable_figure.render(spec, os.path.join(root, 'figure'))
            shapes = Presentation(files['pptx']).slides[0].shapes
            self.assertIn('Yes', [s.text for s in shapes if s.has_text_frame])

    def test_editorial_diagram_sections_subtitle_and_orthogonal_path(self):
        spec = {'nodes': [{'id': 'a', 'text': '传感器', 'subtitle': '模拟信号', 'x': 1, 'y': 2, 'w': 3, 'h': 2},
                          {'id': 'b', 'text': '主控', 'subtitle': '采集与判断', 'x': 6, 'y': 4, 'w': 3, 'h': 2}],
                'sections': [{'text': '01 采集', 'x': 1, 'y': 0.5, 'w': 3},
                             {'text': '02 处理', 'x': 6, 'y': 0.5, 'w': 3}],
                'notes': [{'text': '供电待验证', 'x': 1, 'y': 7, 'w': 4, 'h': 0.8}],
                'edges': [{'from': 'a', 'to': 'b', 'waypoints': [[5, 3], [5, 5]],
                           'to_port': [6, 5]}]}
        with tempfile.TemporaryDirectory() as root:
            files = editable_figure.render(spec, os.path.join(root, 'figure'))
            slides = Presentation(files['pptx']).slides[0].shapes
            content = '\n'.join(s.text for s in slides if s.has_text_frame)
            for text in ('传感器', '模拟信号', '主控', '采集与判断', '01 采集', '02 处理', '供电待验证'):
                self.assertIn(text, content)
            with open(files['layout'], encoding='utf-8') as f:
                layout = json.load(f)
            points = layout['edges'][0]['pts']
            self.assertEqual(len(points), 4)
            self.assertTrue(all(a[0] == b[0] or a[1] == b[1] for a, b in zip(points, points[1:])))

    def test_invalid_waypoint_is_rejected(self):
        spec = {'nodes': [{'id': 'a', 'text': 'A', 'x': 1, 'y': 1, 'w': 2, 'h': 1},
                          {'id': 'b', 'text': 'B', 'x': 5, 'y': 1, 'w': 2, 'h': 1}],
                'edges': [{'from': 'a', 'to': 'b', 'waypoints': [[-1, 2]]}]}
        with tempfile.TemporaryDirectory() as root, self.assertRaises(ValueError):
            editable_figure.render(spec, os.path.join(root, 'figure'))

    def test_port_must_be_on_node_boundary(self):
        spec = {'nodes': [{'id': 'a', 'text': 'A', 'x': 1, 'y': 1, 'w': 2, 'h': 1},
                          {'id': 'b', 'text': 'B', 'x': 5, 'y': 1, 'w': 2, 'h': 1}],
                'edges': [{'from': 'a', 'to': 'b', 'to_port': [6, 1.5]}]}
        with tempfile.TemporaryDirectory() as root, self.assertRaises(ValueError):
            editable_figure.render(spec, os.path.join(root, 'figure'))


if __name__ == '__main__':
    unittest.main()
