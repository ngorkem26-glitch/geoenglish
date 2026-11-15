"""Generate the next curriculum lesson with OpenAI; store validated JSON atomically."""
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


def generate(topic, level, titles):
    from openai import OpenAI
    client = OpenAI(api_key=os.environ['OPENAI_API_KEY'], timeout=60.0, max_retries=2)
    prompt = f'''Produce a UNIQUE, accurate beginner-to-academic English lesson for a Turkish geography student.
Topic: {topic}; CEFR level: {level}. Previous titles: {json.dumps(titles[-25:], ensure_ascii=False)}.
Write clear Turkish instruction, English sentences with Turkish translations, geography examples only when suitable.
Do not invent citations or current facts. Avoid duplicate content. Provide a natural SEO title <=70 chars and meta description <=165 chars.
Return ONLY a JSON object with these fields:
"title": string, "description": string, "seo_title": string, "seo_description": string,
"explanation": plain Turkish text, "content_html": HTML fragment using ONLY h2,h3,p,strong,em,ul,ol,li,blockquote,br,
"vocabulary": array of 5-8 objects {{"english":string,"turkish":string}},
"examples": array of >=3 objects {{"english":string,"turkish":string}},
"quiz": array of >=3 objects {{"question":string,"options":[3 strings],"correct_index":integer 0..2}}.
Every quiz question must have exactly one unambiguous correct answer. No markdown fences, script, styles or attributes.'''
    response = client.responses.create(
        model='gpt-4o-mini',
        instructions='Return a valid JSON object only. No markdown.',
        input=prompt,
        text={'format': {'type': 'json_object'}},
        max_output_tokens=3500,
    )
    if not response.output_text:
        raise ValueError('Empty API response')
    return validate(json.loads(response.output_text))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--topic', default=None)
    parser.add_argument('--level', choices=sorted(LEVELS), default='A1')
    parser.add_argument('--dry-run', action='store_true', help='Show next topic without API usage')
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
    today = datetime.now(ZoneInfo('Europe/Istanbul'))
    digest = hashlib.sha256(f'{level}:{topic.casefold().strip()}'.encode()).hexdigest()[:12]
    lesson_id = 'geo-' + digest
    if any(x.get('id') == lesson_id or (x.get('topic','').casefold().strip() == topic.casefold().strip() and x.get('level') == level) for x in lessons):
        print('Lesson already exists; skipped:', topic)
        return
    print(f'Next lesson: {level} / {topic}')
    if args.dry_run:
        return
    if not os.getenv('OPENAI_API_KEY'):
        raise RuntimeError('OPENAI_API_KEY missing. Add it as a GitHub Actions secret.')
    content = generate(topic, level, [x.get('title', '') for x in lessons])
    lesson = {'id': lesson_id, 'topic': topic, 'level': level,
              'category': 'Coğrafya İngilizcesi', 'created_at': today.isoformat(timespec='seconds'),
              'published': True, 'duration_minutes': 15, 'model': 'gpt-4o-mini', **content}
    db['lessons'].insert(0, lesson)
    atomic_save(DATA, db)
    print('Saved:', lesson['title'])


if __name__ == '__main__':
    main()
