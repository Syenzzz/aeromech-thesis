import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

from docx import Document
import pymupdf

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))
import figure_iface as fi
import figure_review as review
import thesis_build as build


class EndToEndTests(unittest.TestCase):
    def test_generate_review_insert_and_export(self):
        with tempfile.TemporaryDirectory() as root:
            folder = os.path.join(root, '.aeromech')
            os.makedirs(folder)
            with open(os.path.join(folder, 'chapter.md'), 'w', encoding='utf-8') as f:
                f.write('# 第1章 维修方法\n\n维修过程见图1-1。\n\n（图1-1 维修流程）\n\n统计结果见图1-2。\n\n（图1-2 故障统计）\n\n分析见图1-3。\n\n（图1-3 风险矩阵）\n')
            with open(os.path.join(root, 'source.json'), 'w', encoding='utf-8') as f:
                json.dump({'nodes': [{'id': 'a', 'text': '故障检查', 'x': 1, 'y': 1, 'w': 3, 'h': 1},
                                      {'id': 'b', 'text': '维修处理', 'x': 1, 'y': 3, 'w': 3, 'h': 1},
                                      {'id': 'c', 'text': '功能检查', 'x': 1, 'y': 5, 'w': 3, 'h': 1}],
                           'edges': [{'from': 'a', 'to': 'b'}, {'from': 'b', 'to': 'c'}]}, f)
            with open(os.path.join(root, 'chart.json'), 'w', encoding='utf-8') as f:
                json.dump({'type': 'bar', 'categories': ['A', 'B'],
                           'series': [{'name': 'Count', 'values': [3, 5]}]}, f)
            with open(os.path.join(root, 'table.json'), 'w', encoding='utf-8') as f:
                json.dump({'columns': ['Risk', 'Level'], 'rows': [['Leak', 'High']]}, f)
            plan = [{'figure_id': 'FIG-1', 'kind': 'editable', 'source': 'source.json',
                     'out': '.aeromech/artifacts/figures/final/fig1-1.png', 'related_rqs': ['RQ-01']},
                    {'figure_id': 'FIG-2', 'kind': 'editable_chart', 'type': 'stat_bar', 'source': 'chart.json',
                     'out': '.aeromech/artifacts/figures/final/fig1-2.png', 'related_rqs': ['RQ-01']},
                    {'figure_id': 'FIG-3', 'kind': 'editable_table', 'source': 'table.json',
                     'out': '.aeromech/artifacts/figures/final/fig1-3.png', 'related_rqs': ['RQ-01']}]
            fi.save_plan(root, plan)
            review.save_plan(root, plan)
            review.confirm_plan(root)
            for item in plan:
                fid = item['figure_id']
                self.assertEqual(fi.generate_figure(root, fid)['status'], 'GENERATED')
                self.assertEqual(fi.validate_figure(root, fid)['status'], 'VALIDATED')
                image = os.path.join(root, item['out'])
                review.confirm_image(root, fid, image)
                review.confirm_insertion(root, fid, image, plan)
            contract = {'project': {'title': '维修流程示例'}, 'content': {'chapters': ['chapter.md']},
                        'figures': [{'figure_id': item['figure_id'], 'display': f'图1-{index}',
                                     'file': item['out'], 'caption_cn': f'图1-{index} {caption}'}
                                    for index, (item, caption) in enumerate(zip(plan, ['维修流程', '故障统计', '风险矩阵']), 1)]}
            out, _ = build.build_docx(root, contract)
            document = Document(out)
            self.assertEqual(len(document.inline_shapes), 3)
            text = '\n'.join(c.text for t in document.tables for row in t.rows for c in row.cells)
            self.assertIn('图1-1 维修流程', text)
            office = shutil.which('soffice') or r'C:\Program Files\LibreOffice\program\soffice.exe'
            if not os.path.isfile(office):
                self.skipTest('LibreOffice is not installed')
            profile = 'file:///' + os.path.join(root, 'lo-profile').replace('\\', '/')
            run = subprocess.run([office, '-env:UserInstallation=' + profile, '--headless', '--convert-to',
                                  'pdf', '--outdir', root, out], capture_output=True, timeout=90)
            self.assertEqual(run.returncode, 0, run.stderr.decode(errors='replace'))
            pdf = os.path.join(root, os.path.splitext(os.path.basename(out))[0] + '.pdf')
            with open(pdf, 'rb') as f:
                self.assertEqual(f.read(5), b'%PDF-')
            doc = pymupdf.open(pdf)
            self.assertTrue(any(page.get_images() for page in doc))
            self.assertIn('图1-1', ''.join(page.get_text() for page in doc))
            doc.close()
            import figure_visual_qa
            report = figure_visual_qa.run(os.path.dirname(image), pdf=pdf,
                                          plan=fi.plan_path(root), out=root)
            self.assertFalse(any(item['status'] == 'FAIL' for item in report.items))
            self.assertEqual(sum(item['code'] == 'VIS-10' and item['status'] == 'PASS' for item in report.items), 3)
            self.assertTrue(any(item['code'] == 'VIS-11' and item['status'] == 'PASS' and item['evidence'] == 'fig1-2' for item in report.items))
            qa_script = os.path.join(os.path.dirname(build.__file__), 'graph_quality_qa.py')
            qa = subprocess.run([sys.executable, qa_script, '--docx', out, '--pdf', pdf,
                                 '--figdir', os.path.dirname(image), '--out', root],
                                capture_output=True, text=True, encoding='utf-8', timeout=90)
            self.assertEqual(qa.returncode, 0, qa.stdout + qa.stderr)


if __name__ == '__main__':
    unittest.main()
