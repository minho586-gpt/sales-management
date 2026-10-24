"""Optional end-to-end UI smoke test.

Developer prerequisite: pip install playwright, plus a Chromium installation.
Run: python tests/browser_smoke.py
The application itself has no third-party dependencies. This test always uses
an isolated temporary database and never modifies the normal workspace data.
"""
from datetime import datetime, timedelta, timezone
import io
import json
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from urllib.error import URLError
from urllib.request import urlopen
from zipfile import ZipFile

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]


def main():
    now = datetime.now(timezone(timedelta(hours=9))).date()
    next_monday = now - timedelta(days=now.weekday()) + timedelta(days=7)
    browser_errors = []
    failed_responses = []
    with tempfile.TemporaryDirectory(prefix='sales-ui-test-') as temp:
        temp = Path(temp)
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        base = f'http://127.0.0.1:{port}'
        log = open(temp / 'server.log', 'w+')
        process = subprocess.Popen([sys.executable, str(ROOT / 'server.py'), '--host', '127.0.0.1', '--port', str(port), '--db', str(temp / 'test.db')], cwd=ROOT, stdout=log, stderr=log)
        try:
            for attempt in range(100):
                try:
                    with urlopen(base + '/api/data', timeout=1) as response:
                        assert response.status == 200
                    break
                except (URLError, OSError):
                    if process.poll() is not None:
                        raise RuntimeError('Test server exited during startup')
                    time.sleep(0.05)
            else:
                raise RuntimeError('Test server did not start')
            with sync_playwright() as playwright:
                executable = shutil.which('chromium') or shutil.which('chromium-browser')
                browser = playwright.chromium.launch(executable_path=executable, args=['--no-sandbox'])
                context = browser.new_context(viewport={'width': 1440, 'height': 1000}, locale='ko-KR', timezone_id='Asia/Seoul', accept_downloads=True)
                page = context.new_page()
                page.on('pageerror', lambda error: browser_errors.append(str(error)))
                page.on('response', lambda response: failed_responses.append(f'{response.status} {response.url}') if response.status >= 500 else None)
                page.set_default_timeout(10000)

                def step(message):
                    print(message, flush=True)

                def nav(view, title):
                    page.locator(f'.nav-item[href="#{view}"]').click()
                    expect(page.locator('h1')).to_have_text(title)

                def save():
                    page.locator('#save-button').click()
                    expect(page.locator('.modal')).to_have_count(0)

                def delete_record(row):
                    row.locator('[data-action^="delete-"]').click()
                    page.locator('#confirm-delete').click()
                    expect(page.locator('.modal')).to_have_count(0)

                step('1. Dashboard sample metrics and initial rendering')
                page.goto(base)
                expect(page.locator('h1')).to_have_text('대시보드')
                expect(page.locator('.stat-card')).to_have_count(4)
                expect(page.locator('.stat-value').nth(0)).to_have_text('6개사')
                expect(page.locator('.stat-value').nth(1)).to_have_text('4건')
                expect(page.locator('.stat-value').nth(3)).to_have_text('5건')

                step('2. Create, search, inspect, and edit customer')
                nav('customers', '고객사 관리')
                page.locator('.heading-actions [data-action="new-customer"]').click()
                page.locator('.modal').get_by_label('고객사명', exact=False).fill('브라우저테스트 고객')
                page.locator('.modal').get_by_label('업종', exact=True).fill('테스트 제조업')
                page.locator('.modal').get_by_label('담당자', exact=False).fill('테스트 담당자')
                page.locator('.modal').get_by_label('연락처', exact=False).fill('010-0000-1234')
                page.locator('.modal').get_by_label('이메일', exact=True).fill('smoke@example.com')
                page.locator('.modal').get_by_label('주소', exact=False).fill('서울특별시 샘플로 123')
                page.locator('.modal').get_by_label('메모', exact=True).fill('자동화 테스트용 가상 정보')
                save()
                page.locator('#list-search').fill('브라우저테스트')
                expect(page.locator('tbody tr')).to_have_count(1)
                page.locator('[data-action="customer-detail"]').click()
                expect(page.locator('.panel-title').first).to_have_text('브라우저테스트 고객')
                expect(page.locator('.detail-value').filter(has_text='서울특별시 샘플로 123')).to_have_count(1)
                page.locator('[data-action="detail-edit-customer"]').click()
                page.locator('.modal').get_by_label('고객사명', exact=False).fill('브라우저테스트 수정고객')
                save()
                expect(page.locator('.panel-title').first).to_have_text('브라우저테스트 수정고객')

                step('3. Record and update customer activity')
                nav('activities', '영업활동 관리')
                page.locator('.heading-actions [data-action="new-activity"]').click()
                page.locator('.modal').get_by_label('고객사', exact=False).select_option(label='브라우저테스트 수정고객')
                page.locator('.modal').get_by_label('활동일자', exact=False).fill(now.isoformat())
                page.locator('.modal').get_by_label('활동 유형', exact=False).select_option('미팅')
                page.locator('.modal').get_by_label('상담내용', exact=False).fill('테스트 장비 도입을 상담했습니다.')
                page.locator('.modal').get_by_label('다음 진행사항', exact=True).fill('브라우저테스트 후속 제안서 전달')
                page.locator('.modal').get_by_label('다음 진행일', exact=True).fill(next_monday.isoformat())
                save()
                page.locator('#list-search').fill('브라우저테스트')
                expect(page.locator('tbody tr')).to_have_count(1)
                page.locator('tbody [data-action="edit-activity"]').click()
                page.locator('.modal').get_by_label('진행상태', exact=False).select_option('완료')
                save()
                expect(page.locator('tbody .badge')).to_have_text('완료')

                step('4. Multi-item quote calculations and update')
                nav('quotes', '견적 관리')
                page.locator('.heading-actions [data-action="new-quote"]').click()
                page.locator('.modal').get_by_label('견적명', exact=False).fill('브라우저테스트 견적')
                page.locator('.modal').get_by_label('고객사', exact=False).select_option(label='브라우저테스트 수정고객')
                page.locator('.modal').get_by_label('진행상태', exact=False).select_option('협의 중')
                lines = page.locator('.quote-line')
                lines.nth(0).get_by_label('제품명').fill('테스트 모니터')
                lines.nth(0).get_by_label('수량').fill('2')
                lines.nth(0).get_by_label('공급단가').fill('300000')
                page.locator('[data-action="add-item"]').click()
                lines.nth(1).get_by_label('제품명').fill('테스트 의자')
                lines.nth(1).get_by_label('수량').fill('3')
                lines.nth(1).get_by_label('공급단가').fill('120000')
                expect(page.locator('#quote-sum')).to_have_text('960,000원')
                save()
                page.locator('#list-search').fill('브라우저테스트')
                expect(page.locator('tbody tr')).to_have_count(1)
                expect(page.locator('tbody .amount')).to_have_text('960,000원')
                page.locator('tbody .cell-main[data-action="edit-quote"]').click()
                page.locator('.quote-line').nth(0).get_by_label('수량').fill('4')
                page.locator('.modal').get_by_label('진행상태', exact=False).select_option('발송')
                expect(page.locator('#quote-sum')).to_have_text('1,560,000원')
                save()
                expect(page.locator('tbody .amount')).to_have_text('1,560,000원')
                expect(page.locator('tbody .badge')).to_have_text('발송')

                step('5. Add and complete a sales task')
                nav('tasks', '영업업무')
                page.locator('.heading-actions [data-action="new-task"]').click()
                page.locator('.modal').get_by_label('업무명', exact=False).fill('브라우저테스트 업무')
                page.locator('.modal').get_by_label('고객사', exact=True).select_option(label='브라우저테스트 수정고객')
                page.locator('.modal').get_by_label('기한', exact=False).fill(next_monday.isoformat())
                save()
                page.locator('#list-search').fill('브라우저테스트 업무')
                expect(page.locator('.task-row')).to_have_count(1)
                page.get_by_role('checkbox', name='브라우저테스트 업무 완료').check()
                expect(page.locator('.task-row')).to_have_class('task-row task-done')
                expect(page.get_by_role('checkbox', name='브라우저테스트 업무 완료')).to_be_checked()

                step('6. Weekly report navigation and real Excel download')
                nav('reports', '주간보고서')
                expect(page.locator('.report-period')).to_be_visible()
                expect(page.locator('#report-content')).to_contain_text('브라우저테스트 후속 제안서 전달')
                expect(page.locator('#report-content')).to_contain_text('브라우저테스트 견적')
                original_week = page.locator('#report-week').input_value()
                page.locator('[data-action="prev-week"]').click()
                expect(page.locator('#report-week')).not_to_have_value(original_week)
                page.locator('[data-action="this-week"]').click()
                expect(page.locator('#report-week')).to_have_value(original_week)
                expect(page.locator('.report-period')).to_be_visible()
                with page.expect_download() as pending_download:
                    page.locator('[data-action="export-report"]').click()
                excel = pending_download.value
                excel_path = temp / 'weekly-report.xlsx'
                excel.save_as(excel_path)
                with ZipFile(excel_path) as archive:
                    assert archive.testzip() is None
                    assert len([name for name in archive.namelist() if name.startswith('xl/worksheets/sheet')]) == 3

                step('7. JSON backup and restore through the UI')
                nav('settings', '데이터 관리')
                with page.expect_download() as pending_download:
                    page.locator('[data-action="backup"]').click()
                backup_path = temp / 'sales-backup.json'
                pending_download.value.save_as(backup_path)
                backup = json.loads(backup_path.read_text())
                assert len(backup['customers']) == 7
                nav('quotes', '견적 관리')
                page.locator('#list-search').fill('브라우저테스트')
                delete_record(page.locator('tbody tr'))
                expect(page.locator('tbody tr')).to_have_count(0)
                nav('settings', '데이터 관리')
                page.locator('#restore-file').set_input_files(backup_path)
                expect(page.locator('#confirm-restore')).to_be_visible()
                page.locator('#confirm-restore').click()
                expect(page.locator('.modal')).to_have_count(0)
                page.reload()
                expect(page.locator('h1')).to_have_text('데이터 관리')
                nav('quotes', '견적 관리')
                page.locator('#list-search').fill('브라우저테스트')
                expect(page.locator('tbody .amount')).to_have_text('1,560,000원')

                step('8. Customer history reflects stored activity and quote')
                nav('customers', '고객사 관리')
                page.locator('#list-search').fill('브라우저테스트')
                page.locator('[data-action="customer-detail"]').click()
                expect(page.locator('#view-content')).to_contain_text('브라우저테스트 견적')
                expect(page.locator('#view-content')).to_contain_text('테스트 장비 도입을 상담했습니다.')

                step('9. Mobile navigation and page-width overflow check')
                page.set_viewport_size({'width': 390, 'height': 844})
                page.locator('[data-action="menu"]').click()
                expect(page.locator('body')).to_have_class('menu-open')
                page.locator('.nav-item[href="#dashboard"]').click()
                expect(page.locator('h1')).to_have_text('대시보드')
                expect(page.locator('body')).not_to_have_class('menu-open')
                assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), 'Mobile dashboard overflows viewport'
                for view, title in [('quotes', '견적 관리'), ('reports', '주간보고서'), ('settings', '데이터 관리')]:
                    page.locator('[data-action="menu"]').click()
                    page.locator(f'.nav-item[href="#{view}"]').click()
                    expect(page.locator('h1')).to_have_text(title)
                    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), f'Mobile {view} overflows viewport'
                assert not browser_errors, f'Browser errors: {browser_errors}'
                assert not failed_responses, f'HTTP server errors: {failed_responses}'
                context.close()
                browser.close()
                step('PASS: All 9 browser journeys completed; no browser or server errors.')
        except Exception:
            log.flush()
            log.seek(0)
            print('\nTest server log:\n' + log.read(), file=sys.stderr)
            raise
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            log.close()


if __name__ == '__main__':
    main()
