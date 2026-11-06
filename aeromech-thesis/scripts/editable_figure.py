# -*- coding: utf-8 -*-
"""Render explicitly positioned diagram nodes to editable slides and images."""
import os
import textwrap
import math
import json
import unicodedata

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import figure_style as ST
from matplotlib.patches import Ellipse, FancyArrowPatch, FancyBboxPatch, Polygon
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.xmlchemy import OxmlElement
from pptx.util import Cm, Pt


def render(spec, output_base):
    nodes = spec.get('nodes') or []
    edges = spec.get('edges') or []
    sections = spec.get('sections') or []
    notes = spec.get('notes') or []
    ids = [str(n.get('id') or '') for n in nodes]
    if not ids or any(not i for i in ids) or len(set(ids)) != len(ids):
        raise ValueError('Nodes require unique IDs')
    by_id = dict(zip(ids, nodes))
    for node in nodes:
        if not node.get('text') or any(isinstance(node.get(k), bool) or not isinstance(node.get(k), (int, float)) or not math.isfinite(node[k]) for k in ('x', 'y', 'w', 'h')) or node['w'] <= 0 or node['h'] <= 0 or node['x'] < 0 or node['y'] < 0:
            raise ValueError('Node needs text and positive dimensions')
        if node.get('shape', 'rounded') not in ('rounded', 'rectangle', 'diamond', 'ellipse') or node.get('role', 'normal') not in ('normal', 'medium', 'high'):
            raise ValueError('Unsupported node shape or role')
        if node.get('semantic') and node['semantic'] not in ('top_event', 'gate', 'basic_event'):
            raise ValueError('Unsupported semantic role')
        width_chars = max(1, int(node['w'] * 2.2))
        lines = [line for part in str(node['text']).split('\n')
                 for line in (textwrap.wrap(part, width=width_chars, replace_whitespace=False) or [''])]
        if node.get('subtitle'):
            subtitle = str(node['subtitle'])
            units = sum(1 if unicodedata.east_asian_width(c) in ('F', 'W') else .55 for c in subtitle)
            if '\n' in subtitle or units * 11 > node['w'] * 28.35 - 6:
                raise ValueError('Subtitle does not fit; enlarge the node')
            lines.append(subtitle)
        max_font = min(12, node['h'] * 28.35 / (len(lines) * 1.35))
        choices = [size for size in (12, 11.5, 11) if size <= max_font]
        if not choices:
            raise ValueError('Node text does not fit; enlarge the node')
        font_size = choices[0]
        node['_render_lines'] = '\n'.join(lines)
        node['_font_size'] = font_size
    if any(e.get('from') not in by_id or e.get('to') not in by_id for e in edges):
        raise ValueError('Edge references missing node')
    width = max(n['x'] + n['w'] for n in nodes) + 1
    height = max(n['y'] + n['h'] for n in nodes) + 1
    for section in sections:
        if not isinstance(section, dict) or not section.get('text') or any(
                isinstance(section.get(k), bool) or not isinstance(section.get(k), (int, float))
                or not math.isfinite(section[k]) or section[k] < 0 for k in ('x', 'y', 'w')) or not section['w']:
            raise ValueError('Section needs text and valid x, y and width')
        units = sum(1 if unicodedata.east_asian_width(c) in ('F', 'W') else .55 for c in str(section['text']))
        if '\n' in str(section['text']) or units * 11 > section['w'] * 28.35 - 4:
            raise ValueError('Section title does not fit; enlarge the section')
        width = max(width, section['x'] + section['w'] + 1)
        height = max(height, section['y'] + 1.2)
    for note in notes:
        if not isinstance(note, dict) or not note.get('text') or any(
                isinstance(note.get(k), bool) or not isinstance(note.get(k), (int, float))
                or not math.isfinite(note[k]) or note[k] < 0 for k in ('x', 'y', 'w', 'h')) or not note['w'] or not note['h']:
            raise ValueError('Note needs text and valid x, y, width and height')
        width = max(width, note['x'] + note['w'] + 1)
        height = max(height, note['y'] + note['h'] + .5)
    for edge in edges:
        points = edge.get('waypoints', [])
        if not isinstance(points, list) or any(
                not isinstance(p, (tuple, list)) or len(p) != 2 or any(
                    isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0
                    for v in p) or p[0] > width or p[1] > height for p in points):
            raise ValueError('Waypoints must be finite points inside the figure')
        for key, ref in (('from_port', edge['from']), ('to_port', edge['to'])):
            if key not in edge:
                continue
            point, node = edge[key], by_id[ref]
            if (not isinstance(point, (list, tuple)) or len(point) != 2 or
                    any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in point)):
                raise ValueError('Port must be a point on the node boundary')
            px, py = point
            left, top, right, bottom = node['x'], node['y'], node['x'] + node['w'], node['y'] + node['h']
            if not (left <= px <= right and top <= py <= bottom and
                    (math.isclose(px, left, abs_tol=1e-8) or math.isclose(px, right, abs_tol=1e-8) or
                     math.isclose(py, top, abs_tol=1e-8) or math.isclose(py, bottom, abs_tol=1e-8))):
                raise ValueError('Port must be a point on the node boundary')
    deck = Presentation()
    deck.slide_width, deck.slide_height = Cm(width), Cm(height)
    slide = deck.slides.add_slide(deck.slide_layouts[6])
    fig, ax = plt.subplots(figsize=(width / 2.54, height / 2.54))
    fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
    ax.set_xlim(0, width)
    ax.set_ylim(height, 0)
    ax.axis('off')
    plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
    measured_texts = []
    boxes = []
    layout_edges = []
    for section in sections:
        label = slide.shapes.add_textbox(Cm(section['x']), Cm(section['y']), Cm(section['w']), Cm(0.6))
        label.text_frame.margin_left = label.text_frame.margin_right = 0
        label.text_frame.margin_top = label.text_frame.margin_bottom = 0
        label.text_frame.vertical_anchor = MSO_ANCHOR.MIDDLE
        label.text_frame.text = str(section['text'])
        p = label.text_frame.paragraphs[0]
        p.font.name, p.font.size, p.font.bold = 'Microsoft YaHei', Pt(11), True
        p.font.color.rgb = RGBColor.from_string(ST.COLOR_PALETTE['text'][1:])
        artist = ax.text(section['x'], section['y'] + 0.3, str(section['text']), va='center',
                         fontsize=11, fontweight='bold', color=ST.COLOR_PALETTE['text'])
        measured_texts.append(('__note__', artist, 11))
        ax.plot([section['x'], section['x'] + section['w']], [section['y'] + 0.75] * 2,
                color=ST.COLOR_PALETTE['grid'], linewidth=0.7)
        rule = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Cm(section['x']), Cm(section['y'] + 0.75),
                                          Cm(section['x'] + section['w']), Cm(section['y'] + 0.75))
        rule.line.color.rgb = RGBColor.from_string(ST.COLOR_PALETTE['grid'][1:])
        rule.line.width = Pt(0.7)
        for ref in rule._element.xpath('./p:style/a:effectRef'):
            ref.set('idx', '0')
    for note in notes:
        label = slide.shapes.add_textbox(Cm(note['x']), Cm(note['y']), Cm(note['w']), Cm(note['h']))
        label.text_frame.margin_left = label.text_frame.margin_right = 0
        label.text_frame.margin_top = label.text_frame.margin_bottom = 0
        label.text_frame.vertical_anchor = MSO_ANCHOR.MIDDLE
        label.text_frame.text = str(note['text'])
        p = label.text_frame.paragraphs[0]
        p.font.name, p.font.size = 'Microsoft YaHei', Pt(11)
        p.font.color.rgb = RGBColor.from_string(ST.COLOR_PALETTE['text'][1:])
        artist = ax.text(note['x'], note['y'] + note['h'] / 2, str(note['text']), va='center',
                         fontsize=11, color=ST.COLOR_PALETTE['text'])
        measured_texts.append(('__note__', artist, 11))
    for node in nodes:
        x, y, w, h = (node[k] for k in ('x', 'y', 'w', 'h'))
        kind = node.get('shape', 'rounded')
        role = node.get('role', 'normal')
        fill_key, stroke_key = {'normal': ('fill_alt', 'success'), 'medium': ('accent_tint', 'accent'),
                                'high': ('risk_tint', 'risk')}[role]
        fill, stroke = ST.COLOR_PALETTE[fill_key][1:], ST.COLOR_PALETTE[stroke_key][1:]
        if node.get('semantic'):
            border, background, _ = ST.SEMANTIC_COLORS[node['semantic']]
            fill = ST.COLOR_PALETTE[background][1:]
            stroke = ST.COLOR_PALETTE[border][1:]
        ppt_shapes = {'rounded': MSO_SHAPE.ROUNDED_RECTANGLE, 'rectangle': MSO_SHAPE.RECTANGLE,
                      'diamond': MSO_SHAPE.DIAMOND, 'ellipse': MSO_SHAPE.OVAL}
        shape = slide.shapes.add_shape(ppt_shapes[kind], Cm(x), Cm(y), Cm(w), Cm(h))
        shape.fill.solid()
        shape.fill.fore_color.rgb = RGBColor.from_string(fill)
        shape.line.color.rgb = RGBColor.from_string(stroke)
        shape._element.spPr.append(OxmlElement('a:effectLst'))
        for ref in shape._element.xpath('./p:style/a:effectRef'):
            ref.set('idx', '0')
        shape.text_frame.text = node['_render_lines']
        shape.text_frame.vertical_anchor = MSO_ANCHOR.MIDDLE
        shape.text_frame.margin_left = shape.text_frame.margin_right = Pt(2)
        shape.text_frame.margin_top = shape.text_frame.margin_bottom = Pt(1)
        for paragraph in shape.text_frame.paragraphs:
            paragraph.alignment = PP_ALIGN.CENTER
            paragraph.font.size = Pt(node['_font_size'])
            paragraph.font.name = 'Microsoft YaHei'
            paragraph.font.color.rgb = RGBColor.from_string('1F2933')
        if node.get('subtitle'):
            shape.text_frame.clear()
            for i, value in enumerate((str(node['text']), str(node['subtitle']))):
                p = shape.text_frame.paragraphs[0] if i == 0 else shape.text_frame.add_paragraph()
                p.text, p.alignment = value, PP_ALIGN.CENTER
                p.font.name, p.font.size, p.font.bold = 'Microsoft YaHei', Pt(node['_font_size'] if i == 0 else 11), i == 0
                p.font.color.rgb = RGBColor.from_string(ST.COLOR_PALETTE['text'][1:])
        if kind == 'ellipse':
            patch = Ellipse((x + w / 2, y + h / 2), w, h, facecolor='#' + fill, edgecolor='#' + stroke)
        elif kind == 'diamond':
            patch = Polygon([(x + w / 2, y), (x + w, y + h / 2), (x + w / 2, y + h), (x, y + h / 2)], facecolor='#' + fill, edgecolor='#' + stroke)
        else:
            box = 'round,pad=0.02,rounding_size=0.1' if kind == 'rounded' else 'square,pad=0'
            patch = FancyBboxPatch((x, y), w, h, boxstyle=box, facecolor='#' + fill, edgecolor='#' + stroke)
        ax.add_patch(patch)
        if node.get('subtitle'):
            for value, ypos, size, color, weight in ((str(node['text']), y + h * .36, node['_font_size'], ST.COLOR_PALETTE['text'], 'bold'),
                                                     (str(node['subtitle']), y + h * .68, 11, ST.COLOR_PALETTE['text'], 'normal')):
                artist = ax.text(x + w / 2, ypos, value, ha='center', va='center', fontsize=size, color=color, fontweight=weight)
                measured_texts.append((node['id'], artist, size))
        else:
            text_artist = ax.text(x + w / 2, y + h / 2, node['_render_lines'], ha='center', va='center', fontsize=node['_font_size'], color=ST.COLOR_PALETTE['text'])
            measured_texts.append((node['id'], text_artist, node['_font_size']))
        boxes.append({'id': node['id'], 'x': x, 'y': height - y - h, 'w': w, 'h': h,
                      'fill': '#' + fill, 'stroke': '#' + stroke, 'text_color': ST.COLOR_PALETTE['text'],
                      'role': node.get('semantic'), 'text': str(node['text'])})
    for edge in edges:
        a, b = by_id[edge['from']], by_id[edge['to']]
        ac = (a['x'] + a['w'] / 2, a['y'] + a['h'] / 2)
        bc = (b['x'] + b['w'] / 2, b['y'] + b['h'] / 2)
        dx, dy = bc[0] - ac[0], bc[1] - ac[1]
        if dx == 0 and dy == 0:
            raise ValueError('Connected nodes must have distinct centers')
        def boundary(node, center, vx, vy):
            scales = []
            if vx:
                scales.append(node['w'] / (2 * abs(vx)))
            if vy:
                scales.append(node['h'] / (2 * abs(vy)))
            scale = min(scales)
            return center[0] + vx * scale, center[1] + vy * scale
        waypoints = [tuple(p) for p in edge.get('waypoints', [])]
        first, last = (waypoints[0], waypoints[-1]) if waypoints else (bc, ac)
        if first == ac or last == bc:
            raise ValueError('Waypoint cannot coincide with a node center')
        start = tuple(edge['from_port']) if 'from_port' in edge else boundary(a, ac, first[0] - ac[0], first[1] - ac[1])
        end = tuple(edge['to_port']) if 'to_port' in edge else boundary(b, bc, last[0] - bc[0], last[1] - bc[1])
        points = [start] + waypoints + [end]
        if any(p == q for p, q in zip(points, points[1:])):
            raise ValueError('Consecutive edge points must differ')
        for i, (p, q) in enumerate(zip(points, points[1:])):
            line = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Cm(p[0]), Cm(p[1]), Cm(q[0]), Cm(q[1]))
            line.line.color.rgb = RGBColor.from_string('315F61')
            for ref in line._element.xpath('./p:style/a:effectRef'):
                ref.set('idx', '0')
            if i == len(points) - 2:
                arrow = OxmlElement('a:tailEnd')
                arrow.set('type', 'triangle')
                line.line._get_or_add_ln().append(arrow)
            ax.add_patch(FancyArrowPatch(p, q, arrowstyle='->' if i == len(points) - 2 else '-',
                                         mutation_scale=12, color='#315F61', shrinkA=0, shrinkB=0))
        layout_edges.append({'id': str(len(layout_edges) + 1),
                             'pts': [[p[0], height - p[1]] for p in points]})
        if edge.get('label'):
            mx, my = (start[0] + end[0]) / 2, (start[1] + end[1]) / 2
            label = slide.shapes.add_textbox(Cm(mx + 0.1), Cm(my - 0.25), Cm(2), Cm(0.5))
            label.text_frame.text = str(edge['label'])
            label.text_frame.paragraphs[0].font.size = Pt(11.5)
            label.text_frame.paragraphs[0].font.color.rgb = RGBColor.from_string('1F2933')
            edge_text = ax.text(mx + 0.1, my, str(edge['label']), va='center', fontsize=11.5, color='#1F2933')
            measured_texts.append(('__note__', edge_text, 11.5))
    os.makedirs(os.path.dirname(os.path.abspath(output_base)), exist_ok=True)
    result = {kind: output_base + '.' + kind for kind in ('pptx', 'png', 'svg')}
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    inverse = ax.transData.inverted()
    texts = []
    for node_id, artist, font_size in measured_texts:
        extent = artist.get_window_extent(renderer=renderer)
        x0, y0 = inverse.transform((extent.x0, extent.y0))
        x1, y1 = inverse.transform((extent.x1, extent.y1))
        texts.append({'box': node_id, 'x0': x0, 'x1': x1, 'y0': height - y0,
                      'y1': height - y1, 'fs': font_size})
    result['layout'] = output_base + '.layout.json'
    with open(result['layout'], 'w', encoding='utf-8') as f:
        json.dump({'name': os.path.basename(output_base), 'w_cm': width, 'h_cm': height,
                   'dpi': 300, 'figure_kind': 'editable_diagram',
                   'pixel_width': int(width / 2.54 * 300), 'pixel_height': int(height / 2.54 * 300),
                   'boxes': boxes, 'edges': layout_edges, 'texts': texts,
                   'min_font_pt': min(t['fs'] for t in texts)}, f, ensure_ascii=False, indent=2)
    deck.save(result['pptx'])
    fig.savefig(result['png'], dpi=300, facecolor='white')
    fig.savefig(result['svg'], facecolor='white')
    plt.close(fig)
    return result
