#!/usr/bin/env python3
"""영업관리 시스템: Python 표준 라이브러리만 사용하는 로컬 웹 서버."""
from __future__ import annotations

import argparse
from contextlib import closing
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
import json
import errno
import math
from pathlib import Path
import re
import sqlite3
from urllib.parse import parse_qs, unquote, urlsplit
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parent
ENTITIES = ('customers', 'activities', 'quotes', 'tasks')
PENDING_QUOTES = ('작성 중', '발송', '협의 중')
MAX_BODY = 8 * 1024 * 1024
SEOUL = timezone(timedelta(hours=9))
FIELD_LABELS = {'name': '이름', 'contact': '담당자', 'phone': '연락처', 'email': '이메일', 'address': '주소', 'industry': '업종', 'notes': '메모', 'date': '일자', 'validUntil': '유효기한', 'dueDate': '예정일', 'nextDate': '다음 일정', 'content': '상담내용', 'nextStep': '다음 진행사항', 'title': '제목', 'status': '진행상태', 'type': '활동유형'}


class ValidationError(ValueError):
    pass


def today():
    return datetime.now(SEOUL).date()


def text_field(data, key, required=False, limit=4000):
    value = data.get(key, '')
    if not isinstance(value, str):
        raise ValidationError(f'{FIELD_LABELS.get(key, key)}: 올바른 글자를 입력해 주세요.')
    value = value.strip()
    if required and not value:
        raise ValidationError(f'{FIELD_LABELS.get(key, key)}: 필수 항목을 입력해 주세요.')
    if len(value) > limit:
        raise ValidationError(f'{FIELD_LABELS.get(key, key)}: {limit}자 이내로 입력해 주세요.')
    return value


def date_field(data, key, required=True):
    value = text_field(data, key, required, 10)
    if not value and not required:
        return ''
    try:
        parsed = date.fromisoformat(value)
        if parsed.isoformat() != value:
            raise ValueError()
    except ValueError:
        raise ValidationError(f'{FIELD_LABELS.get(key, key)}: 날짜를 YYYY-MM-DD 형식으로 입력해 주세요.') from None
    return value


def choice(data, key, choices, default):
    value = data.get(key, default)
    if value not in choices:
        raise ValidationError(f'{FIELD_LABELS.get(key, key)}: 올바른 상태 또는 유형을 선택해 주세요.')
    return value


def customer_id(data, required=True):
    value = data.get('customerId')
    if value is None and not required:
        return None
    if type(value) is not int or value <= 0:
        raise ValidationError('고객사를 선택해 주세요.')
    return value


def number(value, name, positive=False, maximum=10**12):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValidationError(f'{name}: 올바른 숫자를 입력해 주세요.')
    if value < 0 or (positive and value == 0) or value > maximum:
        raise ValidationError(f'{name}: 허용 범위의 숫자를 입력해 주세요.')
    return value


def validate(entity, data):
    if not isinstance(data, dict):
        raise ValidationError('입력 데이터는 JSON 객체여야 합니다.')
    if entity == 'customers':
        result = {key: text_field(data, key, key == 'name', 200 if key != 'notes' else 4000)
                  for key in ('name', 'contact', 'phone', 'email', 'address', 'industry', 'notes')}
    elif entity == 'activities':
        result = {'customerId': customer_id(data), 'date': date_field(data, 'date'),
                  'type': choice(data, 'type', ('방문', '전화', '이메일', '미팅'), '방문'),
                  'content': text_field(data, 'content', True),
                  'nextStep': text_field(data, 'nextStep'), 'nextDate': date_field(data, 'nextDate', False),
                  'status': choice(data, 'status', ('예정', '진행 중', '완료'), '예정')}
    elif entity == 'quotes':
        items = data.get('items')
        if not isinstance(items, list) or not 1 <= len(items) <= 100:
            raise ValidationError('견적 제품을 1개 이상, 100개 이하로 등록해 주세요.')
        clean_items = []
        for item in items:
            if not isinstance(item, dict):
                raise ValidationError('제품 정보를 확인해 주세요.')
            clean_items.append({'name': text_field(item, 'name', True, 200),
                                'quantity': number(item.get('quantity'), '수량', True, 10**6),
                                'unitPrice': number(item.get('unitPrice'), '공급단가')})
        if sum(Decimal(str(x['quantity'])) * Decimal(str(x['unitPrice'])) for x in clean_items) > 10**15:
            raise ValidationError('견적 총액은 1,000조 원 이내로 입력해 주세요.')
        result = {'customerId': customer_id(data), 'title': text_field(data, 'title', True, 200),
                  'date': date_field(data, 'date'), 'validUntil': date_field(data, 'validUntil', False),
                  'status': choice(data, 'status', (*PENDING_QUOTES, '수주', '실주'), '작성 중'),
                  'items': clean_items}
        if result['validUntil'] and result['validUntil'] < result['date']:
            raise ValidationError('견적 유효기한은 견적일 이후여야 합니다.')
    elif entity == 'tasks':
        result = {'customerId': customer_id(data, False), 'title': text_field(data, 'title', True, 200),
                  'dueDate': date_field(data, 'dueDate'),
                  'status': choice(data, 'status', ('미완료', '완료'), '미완료')}
    else:
        raise ValidationError('지원하지 않는 항목입니다.')
    return result


def quote_amount(quote):
    return float(sum(Decimal(str(i['quantity'])) * Decimal(str(i['unitPrice'])) for i in quote['items']))


def sample_data():
    now = today()
    monday = now - timedelta(days=now.weekday())
    d = lambda offset: (now + timedelta(days=offset)).isoformat()
    next_d = lambda offset: (monday + timedelta(days=7 + offset)).isoformat()
    customers = [
        {'id': 1, 'name': '한빛테크', 'contact': '김서연', 'phone': '010-0000-1001', 'email': 'sample1@example.com', 'address': '서울특별시 성동구 샘플로 12', 'industry': 'IT · 제조', 'notes': '샘플 고객입니다. 스마트 오피스 장비 도입 검토 중'},
        {'id': 2, 'name': '그린솔루션', 'contact': '이준호', 'phone': '010-0000-1002', 'email': 'sample2@example.com', 'address': '경기도 성남시 예시로 28', 'industry': '환경 · 에너지', 'notes': '샘플 고객입니다. 친환경 설비 신규 프로젝트'},
        {'id': 3, 'name': '모던웍스', 'contact': '박지민', 'phone': '010-0000-1003', 'email': 'sample3@example.com', 'address': '서울특별시 마포구 가상로 7', 'industry': '디자인 · 유통', 'notes': '샘플 고객입니다. 사무실 확장에 따른 추가 주문 예정'},
        {'id': 4, 'name': '넥스트모빌리티', 'contact': '정우진', 'phone': '010-0000-1004', 'email': 'sample4@example.com', 'address': '경기도 수원시 샘플로 36', 'industry': '모빌리티', 'notes': '샘플 고객입니다. 신규 거래 상담'},
        {'id': 5, 'name': '온유컴퍼니', 'contact': '최하은', 'phone': '010-0000-1005', 'email': 'sample5@example.com', 'address': '인천광역시 연수구 예시로 45', 'industry': '서비스', 'notes': '샘플 고객입니다. 정기 거래 고객'},
        {'id': 6, 'name': '블루리버', 'contact': '윤도현', 'phone': '010-0000-1006', 'email': 'sample6@example.com', 'address': '서울특별시 영등포구 가상로 19', 'industry': '물류 · 유통', 'notes': '샘플 고객입니다. 하반기 공급 계약 검토'}]
    activities = [
        {'id': 1, 'customerId': 1, 'date': d(0), 'type': '방문', 'content': '신규 사무기기 도입 관련 요구사항을 확인했습니다.', 'nextStep': '요구사항을 반영한 최종 견적서 전달', 'nextDate': next_d(0), 'status': '완료'},
        {'id': 2, 'customerId': 2, 'date': monday.isoformat(), 'type': '미팅', 'content': '친환경 설비 프로젝트 일정과 예산을 협의했습니다.', 'nextStep': '제품 사양서 및 제안서 발송', 'nextDate': next_d(1), 'status': '진행 중'},
        {'id': 3, 'customerId': 3, 'date': d(-1), 'type': '전화', 'content': '확장 사무실의 추가 장비 수요를 확인했습니다.', 'nextStep': '추가 수량 확정 연락', 'nextDate': d(1), 'status': '진행 중'},
        {'id': 4, 'customerId': 4, 'date': next_d(2), 'type': '방문', 'content': '신규 거래를 위한 제품 시연 및 현장 상담', 'nextStep': '', 'nextDate': '', 'status': '예정'},
        {'id': 5, 'customerId': 5, 'date': d(-3), 'type': '이메일', 'content': '정기 공급 품목과 납기 일정을 안내했습니다.', 'nextStep': '', 'nextDate': '', 'status': '완료'}]
    quotes = [
        {'id': 1, 'customerId': 1, 'title': '스마트 오피스 장비 공급', 'date': d(0), 'validUntil': d(14), 'status': '협의 중', 'items': [{'name': '업무용 노트북', 'quantity': 10, 'unitPrice': 1200000}, {'name': '27인치 모니터', 'quantity': 10, 'unitPrice': 350000}]},
        {'id': 2, 'customerId': 2, 'title': '친환경 모니터링 시스템', 'date': d(-2), 'validUntil': d(12), 'status': '발송', 'items': [{'name': '환경 모니터링 센서', 'quantity': 20, 'unitPrice': 450000}, {'name': '설치 및 설정', 'quantity': 1, 'unitPrice': 2000000}]},
        {'id': 3, 'customerId': 3, 'title': '추가 사무장비 견적', 'date': d(-1), 'validUntil': d(13), 'status': '작성 중', 'items': [{'name': '업무용 데스크', 'quantity': 8, 'unitPrice': 450000}, {'name': '사무용 의자', 'quantity': 8, 'unitPrice': 300000}]},
        {'id': 4, 'customerId': 5, 'title': '정기 소모품 공급', 'date': d(-3), 'validUntil': d(11), 'status': '수주', 'items': [{'name': '사무 소모품 패키지', 'quantity': 10, 'unitPrice': 120000}]},
        {'id': 5, 'customerId': 6, 'title': '물류 관리 단말기 도입', 'date': d(-4), 'validUntil': d(10), 'status': '발송', 'items': [{'name': '휴대용 바코드 단말기', 'quantity': 15, 'unitPrice': 650000}]}]
    tasks = [
        {'id': 1, 'customerId': 1, 'title': '한빛테크 최종 견적 확인', 'dueDate': d(0), 'status': '미완료'},
        {'id': 2, 'customerId': 2, 'title': '제품 사양서 준비', 'dueDate': d(1), 'status': '미완료'},
        {'id': 3, 'customerId': 3, 'title': '추가 발주 수량 확인', 'dueDate': d(-1), 'status': '미완료'},
        {'id': 4, 'customerId': 6, 'title': '물류 단말기 납기 일정 협의', 'dueDate': next_d(0), 'status': '미완료'},
        {'id': 5, 'customerId': None, 'title': '주간 영업 목표 검토', 'dueDate': next_d(4), 'status': '미완료'},
        {'id': 6, 'customerId': 5, 'title': '정기 발주 확인서 전달', 'dueDate': d(-2), 'status': '완료'}]
    return dict(customers=customers, activities=activities, quotes=quotes, tasks=tasks)


class Store:
    def __init__(self, path):
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with closing(self.connect()) as conn, conn:
            conn.execute('CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
            conn.execute('CREATE TABLE IF NOT EXISTS customers (id INTEGER PRIMARY KEY AUTOINCREMENT, payload TEXT NOT NULL)')
            for entity in ENTITIES[1:]:
                conn.execute(f'CREATE TABLE IF NOT EXISTS {entity} (id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id INTEGER REFERENCES customers(id), payload TEXT NOT NULL)')
            if not conn.execute("SELECT 1 FROM metadata WHERE key = 'initialized'").fetchone():
                self._replace(conn, sample_data())
                conn.execute("INSERT INTO metadata VALUES ('initialized', '1')")

    def connect(self):
        conn = sqlite3.connect(self.path, timeout=15)
        conn.execute('PRAGMA foreign_keys = ON')
        return conn

    @staticmethod
    def _all(conn, entity):
        return [dict(json.loads(payload), id=record_id) for record_id, payload in conn.execute(f'SELECT id, payload FROM {entity} ORDER BY id')]

    def all(self):
        with closing(self.connect()) as conn, conn:
            conn.execute('BEGIN')
            return {entity: self._all(conn, entity) for entity in ENTITIES}

    @staticmethod
    def _insert(conn, entity, record, record_id=None):
        record = dict(record)
        record.pop('id', None)
        fields, args = ['payload'], [json.dumps(record, ensure_ascii=False)]
        if entity != 'customers':
            fields.append('customer_id')
            args.append(record['customerId'])
        if record_id is not None:
            fields.append('id')
            args.append(record_id)
        cur = conn.execute(f"INSERT INTO {entity} ({','.join(fields)}) VALUES ({','.join('?' for _ in fields)})", args)
        return dict(record, id=cur.lastrowid)

    def write(self, entity, data, record_id=None):
        with closing(self.connect()) as conn, conn:
            if record_id is not None:
                row = conn.execute(f'SELECT payload FROM {entity} WHERE id=?', (record_id,)).fetchone()
                if not row:
                    raise KeyError()
                data = {**json.loads(row[0]), **data} if isinstance(data, dict) else data
            record = validate(entity, data)
            if entity != 'customers' and record['customerId'] is not None:
                if not conn.execute('SELECT 1 FROM customers WHERE id=?', (record['customerId'],)).fetchone():
                    raise ValidationError('선택한 고객사를 찾을 수 없습니다. 고객사를 다시 선택해 주세요.')
            if record_id is None:
                return self._insert(conn, entity, record)
            payload = json.dumps(record, ensure_ascii=False)
            if entity == 'customers':
                conn.execute('UPDATE customers SET payload=? WHERE id=?', (payload, record_id))
            else:
                conn.execute(f'UPDATE {entity} SET payload=?, customer_id=? WHERE id=?', (payload, record['customerId'], record_id))
            return dict(record, id=record_id)

    def delete(self, entity, record_id):
        with closing(self.connect()) as conn, conn:
            if entity == 'customers':
                for related in ENTITIES[1:]:
                    if conn.execute(f'SELECT 1 FROM {related} WHERE customer_id=?', (record_id,)).fetchone():
                        raise ValidationError('연결된 영업활동, 견적 또는 업무가 있습니다. 해당 내역을 먼저 삭제하거나 다른 고객사로 변경해 주세요.')
            cur = conn.execute(f'DELETE FROM {entity} WHERE id=?', (record_id,))
            if cur.rowcount == 0:
                raise KeyError()

    @staticmethod
    def _replace(conn, data):
        for entity in reversed(ENTITIES):
            conn.execute(f'DELETE FROM {entity}')
        conn.execute('DELETE FROM sqlite_sequence')
        for entity in ENTITIES:
            for record in data[entity]:
                Store._insert(conn, entity, record, record['id'])

    def restore(self, data):
        if not isinstance(data, dict) or type(data.get('version')) is not int or data['version'] != 1:
            raise ValidationError('지원하는 백업 파일(version 1)이 아닙니다.')
        clean = {}
        for entity in ENTITIES:
            rows = data.get(entity)
            if not isinstance(rows, list) or len(rows) > 100000:
                raise ValidationError('백업 파일의 항목 목록을 확인해 주세요.')
            clean[entity] = []
            seen = set()
            for row in rows:
                if not isinstance(row, dict):
                    raise ValidationError('백업 데이터 형식이 올바르지 않습니다.')
                record_id = row.get('id')
                if type(record_id) is not int or not 0 < record_id <= 2**53-1 or record_id in seen:
                    raise ValidationError('백업 파일에 잘못되거나 중복된 ID가 있습니다.')
                seen.add(record_id)
                clean[entity].append(dict(validate(entity, row), id=record_id))
        customer_ids = {row['id'] for row in clean['customers']}
        for entity in ENTITIES[1:]:
            if any(row['customerId'] is not None and row['customerId'] not in customer_ids for row in clean[entity]):
                raise ValidationError('백업 파일에 존재하지 않는 고객사 연결이 있습니다.')
        with closing(self.connect()) as conn, conn:
            self._replace(conn, clean)
        return {entity: len(clean[entity]) for entity in ENTITIES}


def make_report(data, week=None):
    try:
        reference = date.fromisoformat(week) if week else today()
        start = reference - timedelta(days=reference.weekday())
        end, next_start, next_end = start + timedelta(days=6), start + timedelta(days=7), start + timedelta(days=13)
    except (ValueError, OverflowError):
        raise ValidationError('보고서 기준 날짜를 YYYY-MM-DD 형식으로 입력해 주세요.') from None
    s, e, ns, ne = (x.isoformat() for x in (start, end, next_start, next_end))
    customers = {row['id']: row['name'] for row in data['customers']}
    named = lambda row: dict(row, customerName=customers.get(row.get('customerId'), '일반 업무'))
    activities = [named(a) for a in data['activities'] if s <= a['date'] <= e]
    activities.sort(key=lambda a: (a['date'], a['id']))
    quotes = [dict(named(q), amount=quote_amount(q)) for q in data['quotes'] if q['status'] in PENDING_QUOTES]
    tasks = [dict(named(t), source='업무') for t in data['tasks'] if t['status'] != '완료' and ns <= t['dueDate'] <= ne]
    for activity in data['activities']:
        if activity['nextDate'] and activity['nextStep'] and ns <= activity['nextDate'] <= ne:
            tasks.append(named({'id': f"activity-next-{activity['id']}", 'customerId': activity['customerId'], 'title': activity['nextStep'], 'dueDate': activity['nextDate'], 'status': '미완료', 'source': '후속 일정'}))
        if activity['status'] == '예정' and ns <= activity['date'] <= ne:
            tasks.append(named({'id': f"activity-{activity['id']}", 'customerId': activity['customerId'], 'title': activity['content'], 'dueDate': activity['date'], 'status': '미완료', 'source': '예정 활동'}))
    tasks.sort(key=lambda t: (t['dueDate'], t['title']))
    return {'start': s, 'end': e, 'nextStart': ns, 'nextEnd': ne, 'activities': activities, 'quotes': quotes, 'tasks': tasks,
            'totals': {'activityCount': len(activities), 'quoteCount': len(quotes), 'quoteAmount': sum(q['amount'] for q in quotes), 'nextTaskCount': len(tasks)}}


def column_name(index):
    result = ''
    while index:
        index, remainder = divmod(index - 1, 26)
        result = chr(65 + remainder) + result
    return result


def excel_text(value):
    # XML 1.0 cannot contain control characters. Inline strings also prevent formula injection.
    return escape(re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', str(value)))


def make_xlsx(report):
    sheets = [
        ('이번 주 영업활동', [['일자', '고객사', '활동유형', '상담내용', '다음 진행사항', '다음 일정', '진행상태']] + [[a['date'], a['customerName'], a['type'], a['content'], a['nextStep'], a['nextDate'], a['status']] for a in report['activities']]),
        ('진행 중인 견적', [['견적일', '고객사', '견적명', '진행상태', '공급금액 (원, 부가세 제외)']] + [[q['date'], q['customerName'], q['title'], q['status'], q['amount']] for q in report['quotes']]),
        ('다음 주 예정 업무', [['예정일', '고객사', '업무내용', '구분', '진행상태']] + [[t['dueDate'], t['customerName'], t['title'], t['source'], t['status']] for t in report['tasks']])]
    output = BytesIO()
    with ZipFile(output, 'w', ZIP_DEFLATED) as archive:
        types = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
        types += ''.join(f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' for i in range(1, 4)) + '</Types>'
        archive.writestr('[Content_Types].xml', types)
        archive.writestr('_rels/.rels', '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
        workbook = '<?xml version="1.0" encoding="UTF-8"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>'
        workbook += ''.join(f'<sheet name="{name}" sheetId="{i}" r:id="rId{i}"/>' for i, (name, _) in enumerate(sheets, 1)) + '</sheets></workbook>'
        archive.writestr('xl/workbook.xml', workbook)
        relationships = '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        relationships += ''.join(f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i}.xml"/>' for i in range(1, 4))
        relationships += '<Relationship Id="rId4" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>'
        archive.writestr('xl/_rels/workbook.xml.rels', relationships)
        archive.writestr('xl/styles.xml', '<?xml version="1.0" encoding="UTF-8"?><styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><fonts count="2"><font><sz val="11"/><name val="맑은 고딕"/></font><font><b/><sz val="11"/><name val="맑은 고딕"/></font></fonts><fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills><borders count="1"><border/></borders><cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs><cellXfs count="3"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"><alignment vertical="top" wrapText="1"/></xf><xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0"><alignment vertical="top" wrapText="1"/></xf><xf numFmtId="3" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/></cellXfs><cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>')
        for index, (_, rows) in enumerate(sheets, 1):
            xml = '<?xml version="1.0" encoding="UTF-8"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews><cols><col min="1" max="1" width="14" customWidth="1"/><col min="2" max="3" width="24" customWidth="1"/><col min="4" max="7" width="38" customWidth="1"/></cols><sheetData>'
            for row_index, row in enumerate(rows, 1):
                xml += f'<row r="{row_index}">'
                for col_index, value in enumerate(row, 1):
                    ref = f'{column_name(col_index)}{row_index}'
                    if isinstance(value, (int, float)):
                        xml += f'<c r="{ref}" s="2"><v>{value}</v></c>'
                    else:
                        xml += f'<c r="{ref}" t="inlineStr" s="{1 if row_index == 1 else 0}"><is><t xml:space="preserve">{excel_text(value)}</t></is></c>'
                xml += '</row>'
            xml += f'</sheetData><autoFilter ref="A1:{column_name(len(rows[0]))}{len(rows)}"/></worksheet>'
            archive.writestr(f'xl/worksheets/sheet{index}.xml', xml)
    return output.getvalue()


class Handler(SimpleHTTPRequestHandler):
    server_version = 'SalesManagement/1.0'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT / 'public'), **kwargs)

    def end_headers(self):
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'same-origin')
        self.send_header('X-Frame-Options', 'DENY')
        super().end_headers()

    def json_response(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False, allow_nan=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def download(self, body, mime, filename):
        self.send_response(200)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def read_json(self):
        try:
            size = int(self.headers.get('Content-Length', '0'))
        except ValueError:
            raise ValidationError('요청 크기가 올바르지 않습니다.') from None
        if not 0 < size <= MAX_BODY:
            raise ValidationError('파일은 8MB 이하의 JSON 형식이어야 합니다.')
        if self.headers.get_content_type() != 'application/json':
            raise ValidationError('JSON 형식의 요청이 필요합니다.')
        try:
            return json.loads(self.rfile.read(size).decode('utf-8-sig'), parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
        except (UnicodeError, ValueError):
            raise ValidationError('JSON 파일 형식이 올바르지 않습니다.') from None

    def safe_write_request(self):
        # Reject cross-site browser mutations, including form submissions to localhost.
        origin = self.headers.get('Origin')
        if origin and urlsplit(origin).netloc != self.headers.get('Host'):
            raise ValidationError('다른 사이트에서는 데이터를 변경할 수 없습니다.')
        if self.headers.get('Sec-Fetch-Site') == 'cross-site':
            raise ValidationError('다른 사이트에서는 데이터를 변경할 수 없습니다.')

    def api(self, method):
        parsed = urlsplit(self.path)
        path = parsed.path.rstrip('/')
        store = self.server.store
        try:
            if method != 'GET':
                self.safe_write_request()
            if method == 'GET' and path == '/api/data':
                return self.json_response(store.all())
            if method == 'GET' and path in ('/api/report', '/api/report.xlsx'):
                week = parse_qs(parsed.query).get('week', [None])[0]
                report = make_report(store.all(), week)
                if path.endswith('.xlsx'):
                    return self.download(make_xlsx(report), 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', f"weekly-report-{report['start']}.xlsx")
                return self.json_response(report)
            if method == 'GET' and path == '/api/backup':
                data = dict(store.all(), version=1, exportedAt=datetime.now(SEOUL).isoformat())
                return self.download(json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8'), 'application/json; charset=utf-8', f'sales-backup-{today().isoformat()}.json')
            if method == 'POST' and path == '/api/restore':
                counts = store.restore(self.read_json())
                return self.json_response({'ok': True, 'counts': counts})
            match = re.fullmatch(r'/api/(customers|activities|quotes|tasks)(?:/([1-9][0-9]*))?', path)
            if match:
                entity, record_id = match.groups()
                record_id = int(record_id) if record_id else None
                if record_id and record_id > 2**53-1:
                    raise KeyError()
                if method == 'POST' and record_id is None:
                    return self.json_response(store.write(entity, self.read_json()), 201)
                if method == 'PUT' and record_id is not None:
                    return self.json_response(store.write(entity, self.read_json(), record_id))
                if method == 'DELETE' and record_id is not None:
                    store.delete(entity, record_id)
                    return self.json_response({'ok': True})
            return self.json_response({'error': '요청한 주소 또는 작업을 찾을 수 없습니다.'}, 404)
        except ValidationError as exc:
            return self.json_response({'error': str(exc)}, 400)
        except KeyError:
            return self.json_response({'error': '해당 내역을 찾을 수 없습니다. 화면을 새로고침해 주세요.'}, 404)
        except sqlite3.IntegrityError:
            return self.json_response({'error': '연결된 데이터가 변경되었습니다. 화면을 새로고침한 뒤 다시 시도해 주세요.'}, 409)
        except sqlite3.Error:
            return self.json_response({'error': '저장소에 접근할 수 없습니다. 잠시 후 다시 시도해 주세요.'}, 500)
        except (ValueError, TypeError, OverflowError):
            return self.json_response({'error': '입력값의 형식이나 범위를 확인해 주세요.'}, 400)

    def do_GET(self):
        if urlsplit(self.path).path.startswith('/api/'):
            return self.api('GET')
        if not self.safe_static_path():
            return self.send_error(404)
        return super().do_GET()

    def do_HEAD(self):
        if urlsplit(self.path).path.startswith('/api/') or not self.safe_static_path():
            return self.send_error(404)
        return super().do_HEAD()

    def safe_static_path(self):
        raw = unquote(urlsplit(self.path).path)
        if '\x00' in raw or '\\' in raw or any(part.startswith('.') or part == '..' for part in raw.split('/') if part):
            return False
        root = (ROOT / 'public').resolve()
        path = (root / raw.lstrip('/')).resolve()
        return path.is_relative_to(root)

    def list_directory(self, path):
        self.send_error(404)
        return None

    def do_POST(self):
        return self.api('POST')

    def do_PUT(self):
        return self.api('PUT')

    def do_DELETE(self):
        return self.api('DELETE')


def create_server(host='0.0.0.0', port=3000, db=None):
    store = Store(db or ROOT / 'data' / 'sales.db')
    server = ThreadingHTTPServer((host, port), Handler)
    server.daemon_threads = True
    server.store = store
    return server


def main():
    parser = argparse.ArgumentParser(description='영업관리 시스템 실행')
    parser.add_argument('--host', default='0.0.0.0')
    parser.add_argument('--port', type=int, default=3000)
    parser.add_argument('--db', type=Path, default=ROOT / 'data' / 'sales.db')
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error('포트 번호는 1~65535 사이의 숫자로 입력해 주세요.')
    try:
        server = create_server(args.host, args.port, args.db)
    except OSError as exc:
        if exc.errno == errno.EADDRINUSE:
            parser.exit(1, f'포트 {args.port}번이 이미 사용 중입니다. 실행 중인 프로그램을 종료하거나 python server.py --port 3001 명령으로 다른 포트를 사용해 주세요.\n')
        parser.exit(1, '프로그램을 실행할 수 없습니다. 저장 폴더의 쓰기 권한과 --host 설정을 확인해 주세요.\n')
    except sqlite3.Error:
        parser.exit(1, '데이터 파일을 열 수 없습니다. data 폴더의 쓰기 권한을 확인하고, 파일이 손상되었다면 보관한 백업으로 복원해 주세요.\n')
    print(f'영업관리 시스템 실행 중 · 포트 {args.port}', flush=True)
    print(f'데이터 저장 위치: {args.db.resolve()}', flush=True)
    print('종료하려면 Ctrl+C를 누르세요.', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
