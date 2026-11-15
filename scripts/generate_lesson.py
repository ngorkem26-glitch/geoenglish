"""Publish the next prewritten GeoEnglish lesson without paid APIs."""
import argparse
import hashlib
import json
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data' / 'lessons-index.json'
CURRICULUM = ROOT / 'data' / 'curriculum.json'
BANK = ROOT / 'data' / 'lesson-bank.json'
LEVELS = {'A1', 'A2', 'B1', 'B2', 'C1'}
ALLOWED_TAGS = ['h2', 'h3', 'p', 'strong', 'em', 'ul', 'ol', 'li', 'blockquote', 'br']


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def atomic_save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    name = None
    try:
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=path.parent, suffix='.tmp', delete=False) as f:
            name = f.name
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write('\n')
        os.replace(name, path)
    finally:
        if name and os.path.exists(name):
            os.unlink(name)


def choose_topic(lessons, curriculum):
    used = {(x.get('topic', '').casefold().strip(), x.get('level')) for x in lessons}
    for entry in curriculum['topics']:
        if (entry['topic'].casefold().strip(), entry['level']) not in used:
            return entry['topic'], entry['level']
    return None, None


def validate(content):
    from bleach import clean
    for key in ('title', 'description', 'seo_title', 'seo_description', 'explanation', 'content_html'):
        if not isinstance(content.get(key), str) or not content[key].strip():
            raise ValueError(f'Invalid text field: {key}')
    if len(content['seo_title']) > 70 or len(content['seo_description']) > 165:
        raise ValueError('SEO fields too long')
    content['content_html'] = clean(content['content_html'], tags=ALLOWED_TAGS, attributes={}, strip=True)
    if not re.search(r'<h2(?:\s|>)', content['content_html'], re.I):
        raise ValueError('Missing h2 heading')
    for key in ('vocabulary', 'examples', 'quiz'):
        if not isinstance(content.get(key), list) or not content[key]:
            raise ValueError(f'Invalid list: {key}')
    for v in content['vocabulary'] + content['examples']:
        if not isinstance(v, dict) or not all(isinstance(v.get(k), str) and v[k].strip() for k in ('english', 'turkish')):
            raise ValueError('Invalid vocabulary or example')
    for q in content['quiz']:
        if not isinstance(q, dict) or not isinstance(q.get('question'), str):
            raise ValueError('Invalid quiz question')
        opts, answer = q.get('options'), q.get('correct_index')
        if not isinstance(opts, list) or len(opts) < 2 or not all(isinstance(o, str) and o.strip() for o in opts):
            raise ValueError('Invalid quiz options')
        if type(answer) is not int or not 0 <= answer < len(opts):
            raise ValueError('Invalid correct_index')
    return content


def load_prepared(topic, level):
    if not BANK.exists():
        print('No lesson bank found. Create data/lesson-bank.json before publishing.')
        return None
    bank = read_json(BANK)
    entries = bank.get('lessons', [])
    if not isinstance(entries, list):
        raise ValueError('lesson-bank.json: lessons must be a list')
    matches = [entry for entry in entries if entry.get('topic', '').casefold().strip() == topic.casefold().strip() and entry.get('level') == level]
    if not matches:
        print(f'No prepared content for {level} / {topic}; nothing published.')
        return None
    content = {k: v for k, v in matches[0].items() if k not in ('topic', 'level')}
    return validate(content)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--topic', default=None)
    parser.add_argument('--level', choices=sorted(LEVELS), default='A1')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    db = read_json(DATA)
    if not isinstance(db.get('lessons'), list):
        raise ValueError('lessons must be a list')
    lessons = db['lessons']
    if args.topic:
        topic, level = args.topic.strip(), args.level
    else:
        topic, level = choose_topic(lessons, read_json(CURRICULUM))
    if not topic:
        print('Curriculum complete: no new lesson generated.')
        return
    digest = hashlib.sha256(f'{level}:{topic.casefold().strip()}'.encode()).hexdigest()[:12]
    lesson_id = 'geo-' + digest
    if any(x.get('id') == lesson_id or (x.get('topic', '').casefold().strip() == topic.casefold().strip() and x.get('level') == level) for x in lessons):
        print('Lesson already exists; skipped:', topic)
        return
    print(f'Next lesson: {level} / {topic}')
    if args.dry_run:
        return
    content = load_prepared(topic, level)
    if content is None:
        return
    today = datetime.now(ZoneInfo('Europe/Istanbul'))
    lesson = {'id': lesson_id, 'topic': topic, 'level': level,
              'category': 'Coğrafya İngilizcesi', 'created_at': today.isoformat(timespec='seconds'),
              'published': True, 'duration_minutes': 15, 'model': 'prewritten', **content}
    db['lessons'].insert(0, lesson)
    atomic_save(DATA, db)
    print('Saved:', lesson['title'])


if __name__ == '__main__':
    main()
