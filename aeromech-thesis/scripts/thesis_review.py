# -*- coding: utf-8 -*-
"""Track explicit review decisions against the exact project files shown."""
import argparse
import hashlib
import json
import os
import tempfile


def _path(root):
    return os.path.join(root, '.aeromech', 'thesis-review.json')


def _snapshot(root, paths):
    if not paths or len(set(paths)) != len(paths):
        raise ValueError('需要至少一个不重复的审核文件')
    base = os.path.realpath(root)
    snapshot = {}
    for rel in sorted(paths):
        path = os.path.realpath(os.path.join(base, rel))
        if os.path.isabs(rel) or os.path.commonpath([base, path]) != base or not os.path.isfile(path):
            raise ValueError('审核文件不存在或位于项目外')
        h = hashlib.sha256()
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(65536), b''):
                h.update(chunk)
        snapshot[rel.replace('\\', '/')] = h.hexdigest()
    return snapshot


def _load(root):
    try:
        with open(_path(root), encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def confirm(root, category, paths):
    if category not in ('plan', 'outline', 'chapters'):
        raise ValueError('未知审核类别')
    snapshot = _snapshot(root, paths)
    state = _load(root)
    if category == 'chapters':
        state.setdefault(category, {}).update(snapshot)
    else:
        state[category] = snapshot
    dest = _path(root)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=os.path.dirname(dest), suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2, sort_keys=True)
        os.replace(temporary, dest)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def confirmed(root, category, paths):
    try:
        snapshot = _snapshot(root, paths)
        state = _load(root)
        if not isinstance(state, dict):
            return False
        saved = state.get(category) or {}
        if not isinstance(saved, dict):
            return False
        return all(saved.get(path) == digest for path, digest in snapshot.items())
    except (OSError, ValueError, json.JSONDecodeError):
        return False


def main():
    parser = argparse.ArgumentParser(description='记录用户对论文内容的确认')
    parser.add_argument('root')
    parser.add_argument('category', choices=('plan', 'outline', 'chapters'))
    parser.add_argument('files', nargs='+', help='用户已审阅的项目相对路径')
    args = parser.parse_args()
    confirm(os.path.abspath(args.root), args.category, args.files)
    print('已记录确认')


if __name__ == '__main__':
    main()
