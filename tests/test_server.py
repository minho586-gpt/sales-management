"""HTTP integration tests; no external package or network service required."""
import io
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server import Store, create_server, make_report


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / 'sales.db'
        self.server = create_server('127.0.0.1', 0, self.db)
        self.server.RequestHandlerClass = type('QuietHandler', (self.server.RequestHandlerClass,), {'log_message': lambda *args: None})
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f'http://127.0.0.1:{self.server.server_port}'

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.tmp.cleanup()

    def request(self, path, data=None, method='GET', headers=None, raw=False):
        body = json.dumps(data, ensure_ascii=False).encode() if data is not None else None
        request_headers = {'Content-Type': 'application/json', **(headers or {})}
        req = Request(self.base + path, body, request_headers, method=method)
        try:
            response = urlopen(req, timeout=10)
        except HTTPError as error:
            response = error
        with response:
            value = response.read()
            if raw:
                return response.status, value, dict(response.headers)
            return response.status, json.loads(value)

    def all(self):
        status, data = self.request('/api/data')
        self.assertEqual(status, 200)
        return data

    def customer(self, name='통합테스트 고객'):
        status, record = self.request('/api/customers', {'name': name, 'contact': '테스트 담당자', 'phone': '010-0000-9999'}, 'POST')
        self.assertEqual(status, 201)
        return record

    def test_seed_and_crud_survives_store_restart(self):
        data = self.all()
        self.assertEqual(len(data['customers']), 6)
        self.assertTrue(data['activities'] and data['quotes'] and data['tasks'])
        record = self.customer()
        status, updated = self.request(f"/api/customers/{record['id']}", {'name': '수정된 고객', 'address': '서울 예시로'}, 'PUT')
        self.assertEqual(status, 200)
        self.assertEqual(updated['contact'], '테스트 담당자')
        reopened = Store(self.db)
        self.assertIn(updated, reopened.all()['customers'])
        self.assertEqual(self.request(f"/api/customers/{record['id']}", method='DELETE'), (200, {'ok': True}))
        self.assertEqual(self.request(f"/api/customers/{record['id']}", {'name': '없음'}, 'PUT')[0], 404)

    def test_all_entities_roundtrip_and_customer_history_protection(self):
        customer = self.customer()
        customer_id = customer['id']
        payloads = {
            'activities': {'customerId': customer_id, 'date': '2026-10-23', 'type': '방문', 'content': '요구사항 상담', 'nextStep': '견적 발송', 'nextDate': '2026-10-26', 'status': '완료'},
            'quotes': {'customerId': customer_id, 'title': '장비 공급', 'date': '2026-10-23', 'validUntil': '2026-11-06', 'status': '협의 중', 'items': [{'name': '모니터', 'quantity': 2, 'unitPrice': 300000}]},
            'tasks': {'customerId': customer_id, 'title': '후속 통화', 'dueDate': '2026-10-26', 'status': '미완료'}}
        created = {}
        for entity, payload in payloads.items():
            status, record = self.request(f'/api/{entity}', payload, 'POST')
            self.assertEqual(status, 201)
            self.assertEqual({k: v for k, v in record.items() if k != 'id'}, payload)
            created[entity] = record
        self.assertEqual(self.request(f'/api/customers/{customer_id}', method='DELETE')[0], 400)
        status, task = self.request(f"/api/tasks/{created['tasks']['id']}", {'status': '완료'}, 'PUT')
        self.assertEqual(status, 200)
        self.assertEqual(task['status'], '완료')
        for entity, row in created.items():
            self.assertEqual(self.request(f"/api/{entity}/{row['id']}", method='DELETE')[0], 200)
        self.assertEqual(self.request(f'/api/customers/{customer_id}', method='DELETE')[0], 200)

    def test_invalid_input_rejected_without_mutation(self):
        before = self.all()
        invalid = [
            ('customers', {'name': '  '}),
            ('activities', {'customerId': 999999, 'date': '2026-10-23', 'content': '상담'}),
            ('activities', {'customerId': 1, 'date': '2026-02-30', 'content': '상담'}),
            ('activities', {'customerId': True, 'date': '2026-10-23', 'content': '상담'}),
            ('quotes', {'customerId': 1, 'title': '빈 견적', 'date': '2026-10-23', 'items': []}),
            ('quotes', {'customerId': 1, 'title': '잘못된 수량', 'date': '2026-10-23', 'items': [{'name': '제품', 'quantity': -1, 'unitPrice': 100}]}),
            ('quotes', {'customerId': 1, 'title': '날짜 역전', 'date': '2026-10-23', 'validUntil': '2026-10-22', 'items': [{'name': '제품', 'quantity': 1, 'unitPrice': 100}]}),
            ('tasks', {'title': '상태 오류', 'dueDate': '2026-10-23', 'status': '알 수 없음'})]
        for entity, payload in invalid:
            with self.subTest(entity=entity, payload=payload):
                status, result = self.request('/api/' + entity, payload, 'POST')
                self.assertEqual(status, 400)
                self.assertIn('error', result)
        self.assertEqual(self.all(), before)

    def fixture(self):
        customer = {'id': 10, 'name': '보고서 고객'}
        activities = [
            {'id': 1, 'customerId': 10, 'date': '2026-10-19', 'type': '방문', 'content': '월요일 방문', 'status': '완료', 'nextStep': '제안서 발송', 'nextDate': '2026-10-26'},
            {'id': 2, 'customerId': 10, 'date': '2026-10-25', 'type': '전화', 'content': '일요일 전화', 'status': '완료'},
            {'id': 3, 'customerId': 10, 'date': '2026-10-26', 'type': '미팅', 'content': '다음 주 미팅', 'status': '예정'},
            {'id': 4, 'customerId': 10, 'date': '2026-10-18', 'type': '이메일', 'content': '전주 활동', 'status': '완료'}]
        quotes = [
            {'id': 1, 'customerId': 10, 'date': '2026-10-20', 'title': '진행 견적', 'status': '협의 중', 'items': [{'name': '상품', 'quantity': 2, 'unitPrice': 150000}]},
            {'id': 2, 'customerId': 10, 'date': '2026-10-20', 'title': '수주 견적', 'status': '수주', 'items': [{'name': '상품', 'quantity': 1, 'unitPrice': 900000}]},
            {'id': 3, 'customerId': 10, 'date': '2026-10-20', 'title': '실주 견적', 'status': '실주', 'items': [{'name': '상품', 'quantity': 1, 'unitPrice': 900000}]}]
        tasks = [
            {'id': 1, 'customerId': 10, 'title': '다음 월요일 업무', 'dueDate': '2026-10-26', 'status': '미완료'},
            {'id': 2, 'customerId': None, 'title': '다음 일요일 업무', 'dueDate': '2026-11-01', 'status': '미완료'},
            {'id': 3, 'customerId': None, 'title': '완료한 업무', 'dueDate': '2026-10-27', 'status': '완료'},
            {'id': 4, 'customerId': None, 'title': '이번 주 업무', 'dueDate': '2026-10-25', 'status': '미완료'},
            {'id': 5, 'customerId': None, 'title': '다다음 주 업무', 'dueDate': '2026-11-02', 'status': '미완료'}]
        return dict(version=1, customers=[customer], activities=activities, quotes=quotes, tasks=tasks)

    def test_report_week_boundaries_and_pending_amount(self):
        self.assertEqual(self.request('/api/restore', self.fixture(), 'POST')[0], 200)
        status, report = self.request('/api/report?week=2026-10-24')
        self.assertEqual(status, 200)
        self.assertEqual((report['start'], report['end'], report['nextStart'], report['nextEnd']), ('2026-10-19', '2026-10-25', '2026-10-26', '2026-11-01'))
        self.assertEqual([row['id'] for row in report['activities']], [1, 2])
        self.assertEqual(report['totals'], {'activityCount': 2, 'quoteCount': 1, 'quoteAmount': 300000, 'nextTaskCount': 4})
        self.assertEqual({row['source'] for row in report['tasks']}, {'업무', '후속 일정', '예정 활동'})
        self.assertEqual(self.request('/api/report?week=not-a-date')[0], 400)

    def test_report_download_is_real_xlsx_and_escaped(self):
        fixture = self.fixture()
        fixture['activities'][0]['content'] = '=HYPERLINK("https://example.com") & <테스트>'
        self.request('/api/restore', fixture, 'POST')
        status, body, headers = self.request('/api/report.xlsx?week=2026-10-24', raw=True)
        self.assertEqual(status, 200)
        self.assertTrue(body.startswith(b'PK'))
        self.assertEqual(headers['Content-Type'], 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        with ZipFile(io.BytesIO(body)) as zf:
            self.assertEqual(zf.testzip(), None)
            for filename in zf.namelist():
                ET.fromstring(zf.read(filename))
            ns = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
            workbook = ET.fromstring(zf.read('xl/workbook.xml'))
            self.assertEqual(len(workbook.findall('s:sheets/s:sheet', ns)), 3)
            sheet = ET.fromstring(zf.read('xl/worksheets/sheet1.xml'))
            self.assertEqual(len(sheet.findall('s:sheetData/s:row', ns)), 3)
            self.assertFalse(sheet.findall('.//s:f', ns))
            self.assertIn('=HYPERLINK("https://example.com") & <테스트>', [node.text for node in sheet.findall('.//s:t', ns)])
            quote_sheet = ET.fromstring(zf.read('xl/worksheets/sheet2.xml'))
            self.assertEqual(quote_sheet.find('.//s:c[@r="E2"]/s:v', ns).text, '300000.0')

    def test_backup_restore_and_invalid_backup_are_atomic(self):
        before = self.all()
        status, backup_bytes, headers = self.request('/api/backup', raw=True)
        self.assertEqual(status, 200)
        self.assertIn('attachment', headers['Content-Disposition'])
        backup = json.loads(backup_bytes)
        self.assertEqual(backup['version'], 1)
        self.customer('백업 후 새 고객')
        self.assertEqual(self.request('/api/restore', backup, 'POST')[0], 200)
        self.assertEqual(self.all(), before)
        invalid = json.loads(backup_bytes)
        invalid['tasks'][0]['customerId'] = 999999
        self.assertEqual(self.request('/api/restore', invalid, 'POST')[0], 400)
        self.assertEqual(self.all(), before)
        invalid = json.loads(backup_bytes)
        invalid['customers'].append(invalid['customers'][0])
        self.assertEqual(self.request('/api/restore', invalid, 'POST')[0], 400)
        self.assertEqual(self.all(), before)

    def test_empty_restore_does_not_reseed_on_restart(self):
        empty = dict(version=1, **{key: [] for key in ('customers', 'activities', 'quotes', 'tasks')})
        self.assertEqual(self.request('/api/restore', empty, 'POST')[0], 200)
        self.assertEqual(Store(self.db).all(), {key: [] for key in ('customers', 'activities', 'quotes', 'tasks')})
        new = self.customer()
        self.assertEqual(new['id'], 1)

    def test_cross_site_write_and_non_json_blocked(self):
        status, _ = self.request('/api/customers', {'name': '침입'}, 'POST', {'Origin': 'https://different.example'})
        self.assertEqual(status, 400)
        status, _ = self.request('/api/customers', {'name': '잘못된 형식'}, 'POST', {'Content-Type': 'text/plain'})
        self.assertEqual(status, 400)
        self.assertEqual(len(self.all()['customers']), 6)

    def test_path_traversal_and_unknown_route_blocked(self):
        for path in ('/../server.py', '/%2e%2e/server.py', '/.env', '/%2e%2e/data/sales.db', '/api/unknown'):
            with self.subTest(path=path):
                self.assertEqual(self.request(path, raw=True)[0], 404)


if __name__ == '__main__':
    unittest.main()
