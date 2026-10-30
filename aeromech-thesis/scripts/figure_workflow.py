# -*- coding: utf-8 -*-
"""User-facing operations for the figure review workflow."""
import argparse
import json
import os
import sys

import figure_iface as FI
import figure_review as review


def main(argv=None):
    parser = argparse.ArgumentParser(description='论文配图审核')
    parser.add_argument('root')
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('sync-plan')
    commands.add_parser('confirm-plan')
    commands.add_parser('status')
    image = commands.add_parser('confirm-image')
    image.add_argument('--figure', required=True)
    adopt = commands.add_parser('adopt-existing')
    adopt.add_argument('--figure', required=True)
    insert = commands.add_parser('confirm-insertion')
    insert.add_argument('--figure', required=True)
    policy = commands.add_parser('external-policy')
    policy.add_argument('--allow', choices=('yes', 'no'), required=True)
    policy.add_argument('--max-calls', type=int, required=True)
    args = parser.parse_args(argv)
    root = os.path.abspath(args.root)
    try:
        if args.command == 'sync-plan':
            figures = FI.load_plan(root)
            if not figures:
                raise ValueError('配图计划不存在或为空')
            review.save_plan(root, figures)
            print(json.dumps(figures, ensure_ascii=False, indent=2))
        elif args.command == 'confirm-plan':
            figures = FI.load_plan(root)
            if figures != review._load(root).get('plan'):
                raise ValueError('计划已更改，请重新列出清单')
            review.confirm_plan(root)
            print('计划已确认')
        elif args.command == 'adopt-existing':
            figures = FI.load_plan(root) or []
            matches = [s for s in figures if str(s.get('figure_id')) == args.figure]
            if len(matches) != 1 or not review.figure_plan_confirmed(root, args.figure, figures):
                raise ValueError('配图计划未确认')
            item = matches[0]
            rel = item.get('out') or ''
            path = os.path.realpath(os.path.join(root, rel))
            if item.get('kind') != 'user_asset' or not rel or os.path.isabs(rel) or os.path.commonpath([root, path]) != root or not os.path.isfile(path):
                raise ValueError('已有图片路径无效')
            FI.record(root, args.figure, 'GENERATED', artifact=rel,
                      reason='登记用户已有图片', provider='user_asset')
            print('已有图片已登记，请继续确认图片')
        elif args.command in ('confirm-image', 'confirm-insertion'):
            figures = FI.load_plan(root) or []
            matches = [s for s in figures if str(s.get('figure_id')) == args.figure]
            if len(matches) != 1 or not review.figure_plan_confirmed(root, args.figure, figures):
                raise ValueError('配图计划未确认')
            status, entry = FI.current_status(root, args.figure)
            if status not in ('GENERATED', 'VALIDATED', 'EMBEDDED', 'VERIFIED') or not entry.get('artifact'):
                raise ValueError('未找到已生成的图片')
            path = os.path.join(root, entry['artifact'])
            if FI._sha(path) != entry.get('sha256'):
                raise ValueError('图片与生成记录不一致')
            if args.command == 'confirm-image':
                review.confirm_image(root, args.figure, path)
                print('图片已确认')
            else:
                review.confirm_insertion(root, args.figure, path, figures)
                print('图片插入已确认')
        elif args.command == 'external-policy':
            if not review.enabled(root):
                raise ValueError('请先导入配图计划')
            review.set_external_policy(root, args.allow == 'yes', args.max_calls)
            print('外部调用设置已保存')
        else:
            figures = FI.load_plan(root) or []
            result = []
            for figure in figures:
                fid = str(figure.get('figure_id'))
                status, entry = FI.current_status(root, fid)
                artifact = (entry or {}).get('artifact')
                result.append({'figure_id': fid, 'plan_confirmed': review.figure_plan_confirmed(root, fid, figures),
                               'status': status, 'artifact': artifact,
                               'image_confirmed': bool(artifact and review.image_ready(root, fid, os.path.join(root, artifact), figures)),
                               'insertion_confirmed': bool(artifact and review.insertion_ready(root, fid, os.path.join(root, artifact), figures))})
            print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, KeyError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
