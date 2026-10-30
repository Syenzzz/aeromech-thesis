# -*- coding: utf-8 -*-
"""Persist plan and image review decisions against their actual content."""
import hashlib
import json
import os
import sqlite3
import tempfile


def _path(root):
    return os.path.join(root, '.aeromech', 'figures', 'review.json')


def enabled(root):
    return os.path.isfile(_path(root))


def _load(root):
    try:
        with open(_path(root), encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def _save(root, data):
    path = _path(root)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, sort_keys=True, indent=2)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def _digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(',', ':')).encode('utf-8')).hexdigest()


def _figure_digest(root, item):
    source = item.get('source')
    if not source:
        return _digest(item)
    path = os.path.realpath(os.path.join(root, source))
    if os.path.isabs(source) or os.path.commonpath([os.path.realpath(root), path]) != os.path.realpath(root) or not os.path.isfile(path):
        return None
    return _digest({'spec': item, 'source_sha256': _file_digest(path)})


def save_plan(root, figures):
    state = _load(root)
    state['plan'] = figures
    _save(root, state)


def confirm_plan(root):
    state = _load(root)
    if not state.get('plan'):
        raise ValueError('Cannot confirm an empty plan')
    ids = [str(item.get('figure_id') or '') for item in state['plan']]
    if any(not value for value in ids) or len(set(ids)) != len(ids):
        raise ValueError('Figure IDs must be present and unique')
    confirmed = {str(item['figure_id']): _figure_digest(root, item)
                 for item in state['plan']}
    if any(value is None for value in confirmed.values()):
        raise ValueError('Figure source file missing or outside project')
    state['confirmed_plan'] = _digest(state['plan'])
    state['confirmed_figures'] = confirmed
    _save(root, state)


def plan_confirmed(root, figures=None):
    state = _load(root)
    plan = state.get('plan')
    return (bool(plan) and state.get('confirmed_plan') == _digest(plan)
            and (figures is None or _digest(figures) == _digest(plan)))


def figure_plan_confirmed(root, figure_id, figures):
    state = _load(root)
    if _digest(state.get('plan')) != _digest(figures):
        return False
    matches = [item for item in figures if str(item.get('figure_id')) == str(figure_id)]
    if len(matches) != 1:
        return False
    digest = _figure_digest(root, matches[0])
    return bool(digest) and state.get('confirmed_figures', {}).get(str(figure_id)) == digest


def _file_digest(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _manifest_digest(root, path):
    manifest_path = os.path.splitext(path)[0] + '.manifest.json'
    if not os.path.isfile(manifest_path):
        return None
    with open(manifest_path, encoding='utf-8') as f:
        manifest = json.load(f)
    artifacts = manifest.get('artifacts') or {}
    if not artifacts or not all(isinstance(item, dict) and item.get('path') and item.get('sha256') for item in artifacts.values()):
        raise ValueError('Invalid artifact manifest')
    root_path = os.path.realpath(root)
    for item in artifacts.values():
        artifact = os.path.realpath(os.path.join(root_path, item['path']))
        if os.path.commonpath([root_path, artifact]) != root_path or _file_digest(artifact) != item['sha256']:
            raise ValueError('Artifact changed after generation')
    return _file_digest(manifest_path)


def confirm_image(root, figure_id, path):
    state = _load(root)
    digest = _manifest_digest(root, path)
    item = next((entry for entry in state.get('plan', []) if str(entry.get('figure_id')) == str(figure_id)), {})
    if item.get('kind') in ('editable', 'editable_chart', 'editable_table') and digest is None:
        raise ValueError('Editable figure artifact manifest is missing')
    state.setdefault('images', {})[figure_id] = {
        'artifact': _file_digest(path), 'manifest': digest,
        'plan': state.get('confirmed_figures', {}).get(str(figure_id))}
    _save(root, state)


def image_confirmed(root, figure_id, path):
    try:
        item = _load(root).get('images', {}).get(figure_id)
        return (isinstance(item, dict) and item.get('artifact') == _file_digest(path)
                and item.get('manifest') == _manifest_digest(root, path))
    except (OSError, ValueError, KeyError):
        return False


def image_ready(root, figure_id, path, figures):
    state = _load(root)
    image = state.get('images', {}).get(figure_id) or {}
    return (figure_plan_confirmed(root, figure_id, figures)
            and image_confirmed(root, figure_id, path)
            and image.get('plan') == state.get('confirmed_figures', {}).get(figure_id))


def confirm_insertion(root, figure_id, path, figures):
    if not image_ready(root, figure_id, path, figures):
        raise ValueError('Image must be reviewed before insertion')
    state = _load(root)
    state.setdefault('insertions', {})[figure_id] = dict(state['images'][figure_id])
    _save(root, state)


def insertion_ready(root, figure_id, path, figures):
    state = _load(root)
    return (image_ready(root, figure_id, path, figures)
            and state.get('insertions', {}).get(figure_id) == state.get('images', {}).get(figure_id))


def _budget_db(root):
    folder = os.path.join(root, '.aeromech', 'figures')
    os.makedirs(folder, exist_ok=True)
    db = sqlite3.connect(os.path.join(folder, 'external-budget.sqlite3'), timeout=30)
    db.execute('CREATE TABLE IF NOT EXISTS budget (id INTEGER PRIMARY KEY, allowed INTEGER NOT NULL, max_calls INTEGER NOT NULL, used INTEGER NOT NULL)')
    return db


def set_external_policy(root, allowed, max_calls):
    if not isinstance(allowed, bool) or isinstance(max_calls, bool) or not isinstance(max_calls, int) or max_calls < 0:
        raise ValueError('Invalid external policy')
    with _budget_db(root) as db:
        db.execute('INSERT INTO budget VALUES (1, ?, ?, 0) ON CONFLICT(id) DO UPDATE SET allowed=excluded.allowed, max_calls=excluded.max_calls', (int(allowed), max_calls))


def reserve_external_call(root):
    with _budget_db(root) as db:
        cur = db.execute('UPDATE budget SET used=used+1 WHERE id=1 AND allowed=1 AND used<max_calls')
        return cur.rowcount == 1
