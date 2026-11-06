import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))
import thesis_build as build
import pdf_qa
import delivery_gate
import thesis_state
import export_pdf


class DraftDeliveryTests(unittest.TestCase):
    def test_pipeline_passes_contract_paths_and_stops_after_toc_failure(self):
        with tempfile.TemporaryDirectory() as root:
            contract = {'output': {'docx': 'draft.docx', 'pdf': 'draft.pdf'}}
            commands = []
            def fake_step(root, name, cmd, **kwargs):
                commands.append((name, cmd))
                return {'step': name, 'status': 'FAIL' if name == 'toc' else 'PASS',
                        'rc': 1 if name == 'toc' else 0, 'output_tail': ''}
            with patch.object(build, 'load_contract', return_value=(contract, 'contract')), \
                    patch.object(build, '_step', side_effect=fake_step), \
                    patch.object(build.TF, 'select_docx_mode', return_value=(None, None)):
                build.pipeline(root, ['toc', 'pdf'])
            self.assertIn(os.path.join(root, 'draft.docx'), commands[0][1])
            self.assertEqual([name for name, _ in commands], ['toc'])

    def test_export_uses_explicit_input_and_output(self):
        with tempfile.TemporaryDirectory() as root:
            source = os.path.join(root, 'draft.docx')
            output = os.path.join(root, 'draft.pdf')
            with open(source, 'wb') as f:
                f.write(b'draft')
            def convert(src, dst):
                self.assertEqual((src, dst), (source, output))
                with open(dst, 'wb') as f:
                    f.write(b'%PDF-')
            fake = type(sys)('docx2pdf')
            fake.convert = convert
            with patch.dict(sys.modules, {'docx2pdf': fake}), \
                    patch.object(sys, 'argv', ['export_pdf.py', root, source, output]):
                self.assertEqual(export_pdf.main(), 0)

    def test_editorial_appendix_is_excluded_from_chapter_body(self):
        text = '# 第1章 标题\n正文保留\n\n---\n\n## 本章图表点位（待规划确认）\n审阅信息\n\n## 本章待核实事项\n资料缺口'
        result = build._chapter_body(text)
        self.assertIn('正文保留', result)
        self.assertNotIn('审阅信息', result)
        self.assertNotIn('资料缺口', result)
        self.assertIn('正文待核实', build._chapter_body('# 标题\n正文待核实'))

    def test_labels_are_conditional_and_figure_captions_are_generic(self):
        self.assertEqual(pdf_qa.missing_disclosure_labels('基于公开资料进行分析。'), [])
        self.assertIn('【假设/模拟·仅演示方法】', pdf_qa.missing_disclosure_labels('使用模拟数据进行演示。'))
        self.assertEqual(pdf_qa.count_captioned_pages(['图2-1 系统总体结构图', '图5-1 软件监测流程图'], [True, True]), 2)

    def test_required_research_registry_missing_blocks(self):
        with tempfile.TemporaryDirectory() as root:
            thesis_state.main([root, 'init'])
            with open(os.path.join(root, '.aeromech', 'build-contract.yaml'), 'w', encoding='utf-8') as f:
                f.write('research:\n  required: true\n')
            result = delivery_gate.aggregate(root)
            item = next(x for x in result['items'] if x['gate_id'] == 'G-RES-01')
            self.assertEqual(item['status'], 'FAIL')
            self.assertEqual(result['status'], 'BLOCK')


if __name__ == '__main__':
    unittest.main()
