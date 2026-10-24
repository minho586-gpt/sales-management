'use strict';

const $ = (s, root = document) => root.querySelector(s);
const $$ = (s, root = document) => [...root.querySelectorAll(s)];
const escapeHtml = value => String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
const e = escapeHtml;
const won = value => `${Math.round(Number(value) || 0).toLocaleString('ko-KR')}원`;
const number = value => Number(value || 0).toLocaleString('ko-KR');
const today = () => new Intl.DateTimeFormat('sv-SE', {timeZone:'Asia/Seoul'}).format(new Date());
function shiftDate(date, days) { const d = new Date(`${date}T12:00:00Z`); d.setUTCDate(d.getUTCDate() + days); return d.toISOString().slice(0,10); }
function monday(date) { const d = new Date(`${date}T12:00:00Z`); return shiftDate(date, -(d.getUTCDay() + 6) % 7); }
const shortDate = date => date ? date.slice(5).replace('-', '.') : '—';
const dateText = date => date ? date.replaceAll('-', '.') : '—';
const quoteTotal = quote => quote.items.reduce((s, i) => s + Number(i.quantity) * Number(i.unitPrice), 0);
const pending = quote => ['작성 중','발송','협의 중'].includes(quote.status);
const icons = {
 grid:'<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
 customers:'<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M22 21v-2a4 4 0 0 0-3-3.87M15 3.13a4 4 0 0 1 0 7.75"/><circle cx="9" cy="7" r="4"/>',
 activity:'<path d="M8 2v4M16 2v4M3 10h18"/><rect x="3" y="4" width="18" height="18" rx="2"/><path d="m9 16 2 2 4-4"/>',
 quote:'<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z"/><path d="M14 2v6h6M8 13h8M8 17h5"/>',
 report:'<path d="M9 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-4M9 15v-4M13 15V7M17 15v-3M16 3h5v5M21 3l-7 7"/>',
 tasks:'<path d="m3 6 2 2 4-4M13 6h8M3 13l2 2 4-4M13 13h8M3 20l2 2 4-4M13 20h8"/>',
 settings:'<path d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M5.6 18.4l2.1-2.1M16.3 7.7l2.1-2.1"/><circle cx="12" cy="12" r="4"/>',
 plus:'<path d="M12 5v14M5 12h14"/>',
 arrow:'<path d="M5 12h14m-5-5 5 5-5 5"/>',
 down:'<path d="M12 3v12m-5-5 5 5 5-5M4 15v6h16v-6"/>',
 search:'<circle cx="10.5" cy="10.5" r="7.5"/><path d="m16 16 5 5"/>',
 close:'<path d="m6 6 12 12M6 18 18 6"/>',
 more:'<circle cx="5" cy="12" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/>',
 edit:'<path d="m16 3 5 5-12 12-6 1 1-6ZM14 5l5 5"/>',
 trash:'<path d="M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7M14 10v7"/>',
 money:'<rect x="2" y="5" width="20" height="14" rx="2"/><circle cx="12" cy="12" r="3"/><path d="M6 12h.01M18 12h.01"/>',
 trend:'<path d="m3 17 6-6 4 4 8-11M15 4h6v6"/>',
 chevron:'<path d="m9 5 7 7-7 7"/>',
 back:'<path d="m15 5-7 7 7 7"/>',
 shield:'<path d="m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6Z"/><path d="m8 12 3 3 5-6"/>',
 menu:'<path d="M3 6h18M3 12h18M3 18h18"/>',
 check:'<path d="m5 12 4 4L19 6"/>',
 upload:'<path d="M12 16V3m-5 5 5-5 5 5M4 16v5h16v-5"/>'
};
const icon = (name, size=20) => `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${icons[name] || icons.quote}</svg>`;
const state = {data:{customers:[],activities:[],quotes:[],tasks:[]}, view:'dashboard', search:'', filter:'전체', week:monday(today()), report:null, detail:null};
const views = {dashboard:['대시보드','오늘의 영업 현황을 한눈에 확인하세요.'], customers:['고객사 관리','고객 정보부터 거래 이력까지, 한곳에서 관리하세요.'], activities:['영업활동 관리','고객과의 모든 만남과 다음 기회를 기록하세요.'], quotes:['견적 관리','견적을 작성하고 수주까지의 과정을 관리하세요.'], reports:['주간보고서','한 주의 활동을 돌아보고 다음 주를 준비하세요.'], tasks:['영업업무','놓치는 업무 없이, 오늘 해야 할 일을 확인하세요.'], settings:['데이터 관리','소중한 영업 데이터를 안전하게 보관하세요.']};
const customer = id => state.data.customers.find(c => c.id === Number(id));
const customerName = id => customer(id)?.name || '고객사 미지정';
const badgeClass = {'작성 중':'draft','발송':'sent','협의 중':'negotiating','수주':'won','실주':'lost','예정':'scheduled','진행 중':'progress','완료':'done','미완료':'neutral'};
const badge = (status) => `<span class="badge ${badgeClass[status] || 'neutral'}">${e(status)}</span>`;
const button = (label, action, cls='secondary', ico='') => `<button type="button" class="button ${cls}" data-action="${action}">${ico ? icon(ico,16) : ''}${label}</button>`;
function companyCell(id) { const c = customer(id); return `<div class="company-cell"><span class="company-avatar">${e((c?.name || '미').slice(0,1))}</span><div><div class="cell-main">${e(c?.name || '고객사 미지정')}</div><div class="cell-sub">${e(c?.industry || '')}</div></div></div>`; }
const empty = (message, action='', label='새로 등록', ico='quote') => `<div class="empty-state">${icon(ico,32)}<strong>${e(message)}</strong><p>새로운 기록을 등록하면 이곳에 표시됩니다.</p>${action ? button(label,action,'primary','plus'):''}</div>`;
async function api(path, options={}) {
 const res = await fetch(path, {...options, headers:{'Content-Type':'application/json',...options.headers}});
 let body; try { body = await res.json(); } catch { throw new Error('서버의 응답을 읽을 수 없습니다. 프로그램이 실행 중인지 확인해 주세요.'); }
 if (!res.ok) throw new Error(body.error || '요청을 처리하지 못했습니다.');
 return body;
}
function toast(message, error=false) { const root = $('#toast-root'); root.innerHTML = `<div class="toast ${error?'error':''}">${icon(error?'close':'check',18)}${e(message)}</div>`; clearTimeout(toast.timer); toast.timer=setTimeout(()=>root.replaceChildren(),5000); }
async function refresh() { state.data = await api('/api/data'); }
function route() {
 const next=location.hash.slice(1) || 'dashboard'; state.view=views[next]?next:'dashboard'; state.search=''; state.filter='전체'; state.detail=null; state.report=null; render(); if(state.view==='reports') loadReport();
}
function navigate(view) { if(location.hash===`#${view}`) { state.detail=null; render(); } else location.hash=view; }
function render() {
 const [title,subtitle]=views[state.view];
 const incomplete=state.data.tasks.filter(t=>t.status!=='완료').length;
 const nav=[['dashboard','grid','대시보드'],['customers','customers','고객사 관리'],['activities','activity','영업활동 관리'],['quotes','quote','견적 관리'],['reports','report','주간보고서'],['tasks','tasks','영업업무']];
 $('#app').innerHTML=`<div class="app-shell"><div class="mobile-overlay" data-action="close-menu"></div><aside class="sidebar"><a href="#dashboard" class="brand"><span class="brand-mark">${icon('grid',23)}</span><span><span class="brand-name">영업관리 시스템</span><span class="brand-sub">SALES WORKSPACE</span></span></a><div class="nav-caption">워크스페이스</div><nav class="nav-list" aria-label="주 메뉴">${nav.map(([key,ico,label])=>`<a href="#${key}" class="nav-item ${state.view===key?'active':''}" ${state.view===key?'aria-current="page"':''}>${icon(ico)}<span>${label}</span>${key==='tasks'&&incomplete?`<span class="nav-count">${incomplete}</span>`:''}</a>`).join('')}</nav><div class="sidebar-bottom"><a href="#settings" class="nav-item ${state.view==='settings'?'active':''}">${icon('settings')}<span>데이터 관리</span></a><div class="sidebar-note">${icon('shield',18)}<div><strong>나만의 영업 워크스페이스</strong><p>데이터는 서버에 안전하게 저장됩니다.</p></div></div><div class="sample-label"><span></span>로컬 저장 · 외부 서비스 미사용</div></div></aside><main class="main-shell"><header class="topbar"><div class="breadcrumb"><button class="icon-button mobile-menu" data-action="menu" aria-label="메뉴 열기">${icon('menu')}</button><span>워크스페이스</span>${icon('chevron',13)}<strong>${title}</strong></div><div class="topbar-right"><span class="date-label">${new Intl.DateTimeFormat('ko-KR',{timeZone:'Asia/Seoul',year:'numeric',month:'long',day:'numeric',weekday:'short'}).format(new Date())}</span><span class="avatar" title="개인 워크스페이스">나</span></div></header><div class="content"><section class="page-heading"><div><div class="eyebrow">MY SALES WORKSPACE</div><h1>${title}</h1><p class="subtitle">${subtitle}</p></div><div class="heading-actions">${headingAction()}</div></section><div id="view-content">${viewContent()}</div><footer class="footer-note"><span>영업관리 시스템</span><span>입력한 정보는 자동 저장됩니다 · 금액은 부가세 별도</span></footer></div></main></div>`;
 bindViewInputs();
}
function headingAction() {
 if(state.view==='dashboard') return button('영업활동 등록','new-activity','primary','plus');
 if(state.view==='customers') return button('고객사 등록','new-customer','primary','plus');
 if(state.view==='activities') return button('영업활동 등록','new-activity','primary','plus');
 if(state.view==='quotes') return button('견적 작성','new-quote','primary','plus');
 if(state.view==='tasks') return button('업무 등록','new-task','primary','plus');
 if(state.view==='reports') return button('엑셀 다운로드','export-report','primary','down');
 return '';
}
function viewContent() { return ({dashboard:dashboardView,customers:customersView,activities:activitiesView,quotes:quotesView,reports:reportsView,tasks:tasksView,settings:settingsView})[state.view](); }
function panel(title,sub,body,action='',className='') { return `<section class="panel ${className}"><div class="panel-header"><div><h2 class="panel-title">${title}</h2>${sub?`<p class="panel-subtitle">${sub}</p>`:''}</div>${action}</div>${body}</section>`; }
function stat(label,value,foot,ico,color='teal') { return `<article class="stat-card"><div class="stat-top"><span class="stat-label">${label}</span><span class="stat-icon ${color}">${icon(ico,20)}</span></div><div class="stat-value">${value}</div><div class="stat-foot">${foot}</div></article>`; }
function dashboardView() {
 const {customers,activities,quotes,tasks}=state.data;
 const month=today().slice(0,7), active=quotes.filter(pending), monthQuotes=quotes.filter(q=>q.date.startsWith(month)&&q.status!=='실주');
 const openTasks=tasks.filter(t=>t.status!=='완료').sort((a,b)=>a.dueDate.localeCompare(b.dueDate));
 const overdue=openTasks.filter(t=>t.dueDate<today()).length;
 const stats=`<div class="stats-grid">${stat('전체 고객사',`${number(customers.length)}<small>개사</small>`,'함께 성장하는 비즈니스 파트너','customers')}${stat('진행 중인 견적',`${number(active.length)}<small>건</small>`,`총 ${won(active.reduce((s,q)=>s+quoteTotal(q),0))} 협의 중`,'quote','blue')}${stat('이번 달 예상 매출',`${number(monthQuotes.reduce((s,q)=>s+quoteTotal(q),0))}<small>원</small>`,'이번 달 작성 견적 합계 · 실주 제외','money','purple')}${stat('미처리 영업업무',`${number(openTasks.length)}<small>건</small>`,overdue?`<span class="overdue-text">기한이 지난 업무 ${overdue}건</span>`:'차근차근, 다음 기회를 준비하세요','tasks','amber')}</div>`;
 const monthList=Array.from({length:6},(_,i)=>{let d=new Date(`${month}-01T12:00:00Z`);d.setUTCMonth(d.getUTCMonth()-5+i);return d.toISOString().slice(0,7);});
 const sums=monthList.map(m=>quotes.filter(q=>q.date.startsWith(m)&&q.status!=='실주').reduce((s,q)=>s+quoteTotal(q),0)); const max=Math.max(...sums,1);
 const chart=`<div class="panel-body"><div class="chart-legend"><span class="legend-dot"></span>견적 공급금액 <span class="text-muted">실주 제외 · 단위 만원</span></div><div class="chart"><div class="chart-bars">${monthList.map((m,i)=>`<div class="chart-column"><div class="chart-track"><div class="chart-bar ${i===5?'current':''}" style="height:${sums[i] ? Math.max(3,sums[i]/max*85):0}%"><span class="chart-value">${number(Math.round(sums[i]/10000))}</span></div></div><span class="chart-label">${Number(m.slice(5))}월${i===5?' <b>이번 달</b>':''}</span></div>`).join('')}</div></div></div>`;
 const pipeline=`<div class="panel-body pipeline">${['작성 중','발송','협의 중','수주'].map(s=>{const qs=quotes.filter(q=>q.status===s);return `<div class="pipeline-row"><div class="pipeline-label">${badge(s)}<span>${qs.length}건</span></div><div class="pipeline-bar"><div class="pipeline-fill ${badgeClass[s]}" style="width:${quotes.length?qs.length/quotes.length*100:0}%"></div></div><div class="pipeline-value">${won(qs.reduce((sum,q)=>sum+quoteTotal(q),0))}</div></div>`;}).join('')}</div>`;
 const recent=activities.filter(a=>a.date<=today()).sort((a,b)=>b.date.localeCompare(a.date)||b.id-a.id).slice(0,4);
 return `${stats}<div class="dashboard-grid">${panel('월별 영업 흐름','최근 6개월의 견적 규모를 확인하세요',chart,`<span class="badge neutral">최근 6개월</span>`)}${panel('견적 진행 현황','단계별 영업 기회',pipeline,`<a class="link-button" href="#quotes">전체 보기 ${icon('arrow',15)}</a>`)}${panel('최근 영업활동','고객과 함께 쌓아가는 기록',recent.length?`<div class="activity-list">${recent.map(a=>`<button class="activity-row" data-action="edit-activity" data-id="${a.id}"><span class="activity-dot">${icon(a.type==='방문'?'customers':'activity',17)}</span><span class="activity-body"><span class="activity-title">${e(customerName(a.customerId))} <span class="badge neutral">${e(a.type)}</span></span><span class="activity-detail">${e(a.content)}</span></span><span class="activity-time">${shortDate(a.date)}${badge(a.status)}</span></button>`).join('')}</div>`:empty('아직 등록된 영업활동이 없습니다','new-activity','영업활동 등록','activity'),`<a class="link-button" href="#activities">전체 보기 ${icon('arrow',15)}</a>`)}${panel('챙겨야 할 업무',`미완료 업무 ${openTasks.length}건`,openTasks.length?`<div class="task-list">${openTasks.slice(0,4).map(taskRow).join('')}</div>`:empty('모든 업무를 완료했어요','new-task','업무 등록','check'),button('업무 등록','new-task','ghost small','plus'))}</div>${panel('진행 중인 견적','다음 수주로 이어질 기회를 놓치지 마세요',active.length?quoteTable(active.slice().sort((a,b)=>b.date.localeCompare(a.date)).slice(0,5),false):empty('진행 중인 견적이 없습니다','new-quote','견적 작성'),`<a class="link-button" href="#quotes">전체 보기 ${icon('arrow',15)}</a>`)}`;
}
function toolbar(placeholder,statuses=[]) { return `<div class="toolbar"><label class="search-field">${icon('search',18)}<input id="list-search" type="search" placeholder="${placeholder}" aria-label="${placeholder}" value="${e(state.search)}"></label><div class="toolbar-right">${statuses.length?`<select id="list-filter" class="filter-select" aria-label="진행상태 필터">${['전체',...statuses].map(s=>`<option ${s===state.filter?'selected':''}>${s}</option>`).join('')}</select>`:''}<span id="result-count" class="result-count"></span></div></div>`; }
const matches = (...values) => values.some(v=>String(v||'').toLowerCase().includes(state.search.trim().toLowerCase()));
function editActions(entity,id) { return `<div class="row-actions"><button class="icon-button" data-action="edit-${entity}" data-id="${id}" aria-label="수정">${icon('edit',17)}</button><button class="icon-button delete-button" data-action="delete-${entity}" data-id="${id}" aria-label="삭제">${icon('trash',17)}</button></div>`; }
function customersView() {
 if(state.detail) return customerDetail(state.detail);
 return `<section class="panel">${toolbar('고객사명, 담당자, 연락처 검색')}<div id="list-results">${customersResults()}</div></section>`;
}
function customersResults() {
 const list=state.data.customers.filter(c=>matches(c.name,c.contact,c.phone,c.email,c.industry));
 return `<div class="list-count" data-count="${list.length}"></div>${list.length?`<div class="table-wrap"><table><thead><tr><th>고객사</th><th>담당자</th><th>연락처</th><th>진행 중 견적</th><th>거래금액 <small>수주 기준</small></th><th class="text-right">관리</th></tr></thead><tbody>${list.map(c=>{const qs=state.data.quotes.filter(q=>q.customerId===c.id);return `<tr><td><button class="link-button" data-action="customer-detail" data-id="${c.id}">${companyCell(c.id)}</button></td><td><div class="cell-main">${e(c.contact)}</div><div class="cell-sub">${e(c.email)}</div></td><td>${e(c.phone)}</td><td>${qs.filter(pending).length}건</td><td class="amount">${won(qs.filter(q=>q.status==='수주').reduce((s,q)=>s+quoteTotal(q),0))}</td><td>${editActions('customer',c.id)}</td></tr>`;}).join('')}</tbody></table></div>`:empty(state.search?'검색 결과가 없습니다':'아직 등록된 고객사가 없습니다',state.search?'':'new-customer','고객사 등록','customers')}`;
}
function customerDetail(id) {
 const c=customer(id); if(!c) return empty('고객사를 찾을 수 없습니다');
 const activities=state.data.activities.filter(a=>a.customerId===id).sort((a,b)=>b.date.localeCompare(a.date)), quotes=state.data.quotes.filter(q=>q.customerId===id).sort((a,b)=>b.date.localeCompare(a.date));
 return `<div class="customer-detail-header">${button('고객사 목록','customer-list','ghost','back')}<div class="heading-actions">${button('고객 정보 수정',`detail-edit-customer`,'secondary','edit')}${button('영업활동 등록','new-activity','primary','plus')}</div></div>${panel(e(c.name),e(c.industry),`<div class="panel-body detail-grid">${[['담당자',c.contact],['연락처',c.phone],['이메일',c.email],['주소',c.address],['메모',c.notes]].map(([k,v])=>`<div class="detail-item"><div class="detail-label">${k}</div><div class="detail-value">${e(v||'—')}</div></div>`).join('')}</div>`)}${panel('거래 이력',`전체 견적 ${quotes.length}건 · 수주 금액 ${won(quotes.filter(q=>q.status==='수주').reduce((s,q)=>s+quoteTotal(q),0))}`,quotes.length?quoteTable(quotes):empty('등록된 거래 이력이 없습니다','new-quote','견적 작성'))}${panel('영업활동 이력',`총 ${activities.length}건`,activities.length?activityTable(activities):empty('등록된 영업활동이 없습니다','new-activity','영업활동 등록','activity'))}`;
}
function activitiesView() { return `<section class="panel">${toolbar('고객사, 상담내용, 다음 진행사항 검색',['예정','진행 중','완료'])}<div id="list-results">${activitiesResults()}</div></section>`; }
function activitiesResults() {
 const list=state.data.activities.filter(a=>matches(customerName(a.customerId),a.content,a.nextStep)&&(state.filter==='전체'||a.status===state.filter)).sort((a,b)=>b.date.localeCompare(a.date)||b.id-a.id);
 return `<div class="list-count" data-count="${list.length}"></div>${list.length?activityTable(list):empty('표시할 영업활동이 없습니다',state.search?'':'new-activity','영업활동 등록','activity')}`;
}
function activityTable(list) { return `<div class="table-wrap"><table><thead><tr><th>활동일 / 유형</th><th>고객사</th><th>상담내용</th><th>다음 진행사항</th><th>진행상태</th><th class="text-right">관리</th></tr></thead><tbody>${list.map(a=>`<tr><td><div class="cell-main">${dateText(a.date)}</div><div class="cell-sub">${e(a.type)}</div></td><td>${companyCell(a.customerId)}</td><td><div class="cell-content">${e(a.content)}</div></td><td><div class="cell-content">${e(a.nextStep||'—')}</div>${a.nextDate?`<div class="cell-sub">${dateText(a.nextDate)} 예정</div>`:''}</td><td>${badge(a.status)}</td><td>${editActions('activity',a.id)}</td></tr>`).join('')}</tbody></table></div>`; }
function quotesView() { return `<section class="panel">${toolbar('고객사, 견적명, 제품명 검색',['작성 중','발송','협의 중','수주','실주'])}<div id="list-results">${quotesResults()}</div></section>`; }
function quotesResults() {
 const list=state.data.quotes.filter(q=>matches(customerName(q.customerId),q.title,...q.items.map(i=>i.name))&&(state.filter==='전체'||q.status===state.filter)).sort((a,b)=>b.date.localeCompare(a.date)||b.id-a.id);
 return `<div class="list-count" data-count="${list.length}"></div>${list.length?quoteTable(list):empty('표시할 견적이 없습니다',state.search?'':'new-quote','견적 작성')}`;
}
function quoteTable(list,actions=true) { return `<div class="table-wrap"><table><thead><tr><th>견적명</th><th>고객사</th><th>견적일</th><th class="text-right">공급금액</th><th>진행상태</th>${actions?'<th class="text-right">관리</th>':''}</tr></thead><tbody>${list.map(q=>`<tr><td><button class="link-button cell-main" data-action="edit-quote" data-id="${q.id}">${e(q.title)}</button><div class="cell-sub">${e(q.items[0]?.name||'')} ${q.items.length>1?`외 ${q.items.length-1}건`:''}</div></td><td>${companyCell(q.customerId)}</td><td>${dateText(q.date)}</td><td class="text-right amount">${won(quoteTotal(q))}</td><td>${badge(q.status)}</td>${actions?`<td>${editActions('quote',q.id)}</td>`:''}</tr>`).join('')}</tbody></table></div>`; }
function taskRow(t) { const late=t.status!=='완료'&&t.dueDate<today();return `<div class="task-row ${t.status==='완료'?'task-done':''}"><input class="task-check" type="checkbox" data-task-id="${t.id}" ${t.status==='완료'?'checked':''} aria-label="${e(t.title)} 완료"><button class="task-body" data-action="edit-task" data-id="${t.id}"><span class="task-title">${e(t.title)}</span><span class="task-meta">${e(t.customerId?customerName(t.customerId):'일반 업무')}</span></button><span class="task-due ${late?'overdue-text':''}">${t.dueDate===today()?'오늘':shortDate(t.dueDate)}${late?'<small>기한 지남</small>':''}</span>${state.view==='tasks'?`<button class="icon-button delete-button" data-action="delete-task" data-id="${t.id}" aria-label="업무 삭제">${icon('trash',17)}</button>`:''}</div>`; }
function tasksView() { return `<section class="panel">${toolbar('업무명, 고객사 검색',['미완료','완료'])}<div id="list-results">${tasksResults()}</div></section>`; }
function tasksResults() {
 const list=state.data.tasks.filter(t=>matches(t.title,customerName(t.customerId))&&(state.filter==='전체'||t.status===state.filter)).sort((a,b)=>(a.status==='완료')-(b.status==='완료')||a.dueDate.localeCompare(b.dueDate));
 return `<div class="list-count" data-count="${list.length}"></div>${list.length?`<div class="task-list full-list">${list.map(taskRow).join('')}</div>`:empty('표시할 업무가 없습니다','new-task','업무 등록','tasks')}`;
}
function reportsView() { return `<div class="notice info">${icon('report',20)}<span>월요일부터 일요일까지의 영업활동과 현재 진행 중인 견적, 다음 주 예정 업무를 자동으로 모읍니다.</span></div><div class="report-toolbar"><div class="week-control">${button('이전 주','prev-week','secondary small','back')}<label>조회할 주 <input type="date" id="report-week" value="${state.week}" aria-label="조회할 주의 날짜"></label>${button('다음 주','next-week','secondary small','chevron')}</div>${button('이번 주','this-week','ghost small')}</div><div id="report-content">${state.report?reportContent():`<div class="loading">주간보고서를 불러오는 중…</div>`}</div>`; }
let reportRequest=0;
async function loadReport() {
 const request=++reportRequest;
 try { const report=await api(`/api/report?week=${state.week}`); if(request!==reportRequest||state.view!=='reports') return; state.report=report; $('#report-content').innerHTML=reportContent(); }
 catch(err) { if(state.view==='reports'&&request===reportRequest) $('#report-content').innerHTML=`<div class="empty-state"><strong>보고서를 불러오지 못했습니다.</strong><p>${e(err.message)}</p>${button('다시 시도','retry-report','primary')}</div>`; }
}
function reportContent() {
 const r=state.report;
 const metrics=[['이번 주 영업활동',`${r.activities.length}건`],['진행 중인 견적',`${r.quotes.length}건`],['진행 견적 공급금액',won(r.quotes.reduce((s,q)=>s+quoteTotal(q),0))],['다음 주 예정 업무',`${r.tasks.length}건`]];
 return `<div class="report-period"><h2>${dateText(r.start)} — ${dateText(r.end)}</h2><span class="badge neutral">주간 영업보고</span></div><div class="report-summary">${metrics.map(([label,value])=>`<div class="report-metric"><span>${label}</span><strong>${value}</strong></div>`).join('')}</div>${panel('이번 주 영업활동',`${dateText(r.start)} ~ ${dateText(r.end)} 활동일 기준`,r.activities.length?activityTable(r.activities):empty('이번 주에 기록된 영업활동이 없습니다','','','activity'))}${panel('진행 중인 견적 현황','작성 중 · 발송 · 협의 중 상태의 전체 견적',r.quotes.length?quoteTable(r.quotes,false):empty('현재 진행 중인 견적이 없습니다'))}${panel('다음 주 예정 업무',`${dateText(r.nextStart)} ~ ${dateText(r.nextEnd)} · 미완료 업무와 후속 일정`,r.tasks.length?`<div class="table-wrap"><table><thead><tr><th>예정일</th><th>업무 내용</th><th>고객사</th><th>구분</th></tr></thead><tbody>${r.tasks.map(t=>`<tr><td>${dateText(t.dueDate)}</td><td><div class="cell-content">${e(t.title)}</div></td><td>${e(customerName(t.customerId))}</td><td><span class="badge neutral">${e(t.source||'영업업무')}</span></td></tr>`).join('')}</tbody></table></div>`:empty('다음 주에 예정된 업무가 없습니다','','','tasks'))}`;
}
function settingsView() { return `<div class="notice info">${icon('shield',20)}<span>데이터는 이 프로그램이 실행 중인 컴퓨터에 저장됩니다. 브라우저를 닫아도 유지되며, 안전한 보관을 위해 백업을 권장합니다.</span></div><div class="settings-grid"><section class="settings-card"><span class="stat-icon teal">${icon('down',24)}</span><h2>데이터 백업</h2><p>고객사, 영업활동, 견적, 업무를 하나의 JSON 파일로 저장합니다. 다른 컴퓨터로 옮기거나 복원할 때 사용할 수 있습니다.</p>${button('백업 파일 다운로드','backup','primary','down')}</section><section class="settings-card"><span class="stat-icon blue">${icon('upload',24)}</span><h2>백업 복원</h2><p>이 프로그램에서 내려받은 JSON 백업 파일을 선택하세요. 복원하면 현재 데이터가 백업의 내용으로 바뀝니다.</p><input type="file" id="restore-file" accept=".json,application/json" hidden>${button('백업 파일 선택','restore-select','secondary','upload')}</section></div>${panel('저장된 데이터','현재 워크스페이스에 보관된 기록',`<div class="panel-body detail-grid">${[['고객사',state.data.customers.length],['영업활동',state.data.activities.length],['견적',state.data.quotes.length],['영업업무',state.data.tasks.length]].map(([label,value])=>`<div class="detail-item"><span class="detail-label">${label}</span><strong class="detail-value">${value}건</strong></div>`).join('')}</div>`)}<div class="notice"><div><strong>샘플 데이터로 편하게 시작하세요</strong><p>처음 실행할 때만 가상의 고객사와 영업 기록이 추가됩니다. 수정한 내용은 즉시 저장되며 재실행해도 샘플 데이터로 덮어쓰지 않습니다. 실제 정보를 입력하기 전에는 외부에 공개하지 않은 개인용 환경에서 사용하세요.</p></div></div>`; }
function bindViewInputs() {
 const search=$('#list-search'), filter=$('#list-filter');
 if(search) search.addEventListener('input',()=>{state.search=search.value; renderResults();});
 if(filter) filter.addEventListener('change',()=>{state.filter=filter.value; renderResults();});
 updateCount();
 $('#report-week')?.addEventListener('change',evt=>{ if(!evt.target.value) return; state.week=monday(evt.target.value); evt.target.value=state.week; state.report=null; loadReport(); });
 $('#restore-file')?.addEventListener('change',handleRestore);
}
function updateCount() { const count=$('[data-count]')?.dataset.count; if($('#result-count')&&count!==undefined) $('#result-count').textContent=`총 ${count}건`; }
function renderResults() { const fn={customers:customersResults,activities:activitiesResults,quotes:quotesResults,tasks:tasksResults}[state.view]; if(fn) { $('#list-results').innerHTML=fn(); updateCount(); } }

// All input forms use the same server validation and save to SQLite immediately.
let previousFocus=null;
function openModal(title,body,footer='',wide=false) {
 previousFocus=document.activeElement;
 $('#modal-root').innerHTML=`<div class="modal-backdrop"><section class="modal ${wide?'wide':''}" role="dialog" aria-modal="true" aria-labelledby="modal-title"><div class="modal-header"><h2 id="modal-title">${e(title)}</h2><button class="icon-button close-button" data-action="close-modal" aria-label="닫기">${icon('close')}</button></div>${body}${footer}</section></div>`;
 document.body.classList.add('modal-open');
 const form=$('#editor-form'); form?.addEventListener('submit',saveForm);
 setTimeout(()=>$('.modal input:not([type="hidden"]), .modal textarea, .modal button')?.focus(),20);
}
function closeModal() { $('#modal-root').replaceChildren(); document.body.classList.remove('modal-open'); previousFocus?.focus(); }
function field(label,name,value='',type='text',required=false,full=false,extra='') { return `<div class="form-field ${full?'full':''}"><label for="f-${name}">${label}${required?' <span class="required">*</span>':''}</label><input type="${type}" name="${name}" id="f-${name}" value="${e(value)}" ${required?'required':''} ${extra}></div>`; }
function textarea(label,name,value='',required=false) { return `<div class="form-field full"><label for="f-${name}">${label}${required?' <span class="required">*</span>':''}</label><textarea name="${name}" id="f-${name}" rows="3" ${required?'required':''} maxlength="4000">${e(value)}</textarea></div>`; }
function selectField(label,name,options,value,required=false,full=false) { return `<div class="form-field ${full?'full':''}"><label for="f-${name}">${label}${required?' <span class="required">*</span>':''}</label><select name="${name}" id="f-${name}" ${required?'required':''}>${options.map(o=>{const [v,t]=Array.isArray(o)?o:[o,o];return `<option value="${e(v)}" ${String(value)===String(v)?'selected':''}>${e(t)}</option>`;}).join('')}</select></div>`; }
function customerSelect(value,required=true) { return selectField('고객사','customerId',[[required?'':'','고객사를 선택하세요'],...state.data.customers.map(c=>[c.id,c.name])],value,required); }
function editForm(entity,id=null) {
 const list={customer:'customers',activity:'activities',quote:'quotes',task:'tasks'}[entity],record=id?state.data[list].find(x=>x.id===Number(id)):{};
 if(!record) {toast('기록을 찾을 수 없습니다.',true);return;}
 if(entity!=='customer'&&entity!=='task'&&!state.data.customers.length) {toast('먼저 고객사를 등록해 주세요.');editForm('customer');return;}
 const r=record,selectedCustomer=r.customerId||state.detail||''; let body='';
 if(entity==='customer') body=field('고객사명','name',r.name,'text',true,false,'maxlength="200" placeholder="예: 한빛테크"')+field('업종','industry',r.industry,'text',false,false,'maxlength="100" placeholder="예: IT · 소프트웨어"')+field('담당자','contact',r.contact,'text',true,false,'maxlength="100"')+field('연락처','phone',r.phone,'tel',true,false,'maxlength="100" placeholder="예: 02-1234-5678"')+field('이메일','email',r.email,'email',false,false,'maxlength="200"')+field('주소','address',r.address,'text',true,true,'maxlength="200"')+textarea('메모','notes',r.notes);
 if(entity==='activity') body=customerSelect(selectedCustomer)+field('활동일자','date',r.date||today(),'date',true)+selectField('활동 유형','type',['방문','전화','이메일','미팅'],r.type||'방문',true)+selectField('진행상태','status',['예정','진행 중','완료'],r.status||'진행 중',true)+textarea('상담내용','content',r.content,true)+textarea('다음 진행사항','nextStep',r.nextStep)+field('다음 진행일','nextDate',r.nextDate,'date',false)+`<p class="form-hint full">다음 진행일과 진행사항을 함께 입력하면 주간보고서의 후속 일정에 표시됩니다.</p>`;
 if(entity==='task') body=field('업무명','title',r.title,'text',true,true,'maxlength="200" placeholder="예: 견적 발송 후 고객 피드백 확인"')+customerSelect(selectedCustomer,false)+field('기한','dueDate',r.dueDate||today(),'date',true)+selectField('진행상태','status',['미완료','완료'],r.status||'미완료',true);
 if(entity==='quote') body=field('견적명','title',r.title,'text',true,true,'maxlength="200" placeholder="예: 사무실 네트워크 장비 도입"')+customerSelect(selectedCustomer)+selectField('진행상태','status',['작성 중','발송','협의 중','수주','실주'],r.status||'작성 중',true)+field('견적일','date',r.date||today(),'date',true)+field('유효기한','validUntil',r.validUntil||shiftDate(today(),30),'date',true)+`<div class="form-field full quote-items"><div class="quote-items-heading"><label>견적 품목 <span class="required">*</span></label>${button('품목 추가','add-item','ghost small','plus')}</div><div class="quote-item-grid item-head"><span>제품명</span><span>수량</span><span>공급단가 (원)</span><span class="text-right">공급금액</span><span></span></div><div id="quote-lines">${(r.items||[{name:'',quantity:1,unitPrice:0}]).map(itemForm).join('')}</div><div class="quote-total"><span>합계 공급금액 <small>부가세 별도</small></span><strong id="quote-sum">${won(r.items?quoteTotal(r):0)}</strong></div><p class="form-hint">공급금액 = 수량 × 공급단가 · 원 단위 반올림</p></div>`;
 const names={customer:'고객사',activity:'영업활동',quote:'견적',task:'업무'};
 openModal(`${names[entity]} ${id?'수정':entity==='quote'?'작성':'등록'}`,`<form id="editor-form" data-entity="${entity}" data-id="${id||''}"><div class="modal-body"><p class="form-hint"><span class="required">*</span> 표시는 필수 입력 항목입니다.</p><div class="form-grid">${body}</div><p id="form-error" class="form-error" role="alert" hidden></p></div><div class="modal-footer">${button('취소','close-modal','secondary')}<button type="submit" class="button primary" id="save-button">${icon('check',17)}${id?'변경사항 저장':'저장하기'}</button></div></form>`,'',entity==='quote');
 $('#quote-lines')?.addEventListener('input',updateQuoteSum);
}
function itemForm(item={name:'',quantity:1,unitPrice:0}) { return `<div class="quote-item-grid quote-line"><input name="itemName" value="${e(item.name)}" required maxlength="200" aria-label="제품명" placeholder="제품명 입력"><input type="number" name="quantity" value="${item.quantity}" required min="0.01" max="1000000" step="0.01" aria-label="수량"><input type="number" name="unitPrice" value="${item.unitPrice}" required min="0" max="1000000000000" step="1" aria-label="공급단가"><span class="line-total">${won(item.quantity*item.unitPrice)}</span><button class="icon-button" type="button" data-action="remove-item" aria-label="품목 삭제">${icon('close',17)}</button></div>`; }
function updateQuoteSum() { let sum=0; $$('.quote-line').forEach(row=>{const amount=Number($('[name="quantity"]',row).value)*Number($('[name="unitPrice"]',row).value);sum+=amount;$('.line-total',row).textContent=won(amount);});$('#quote-sum').textContent=won(sum); }
async function saveForm(event) {
 event.preventDefault();const form=event.target,entity=form.dataset.entity,id=form.dataset.id;const data=Object.fromEntries(new FormData(form));
 if('customerId' in data) data.customerId=data.customerId?Number(data.customerId):null;
 if(entity==='quote') {data.items=$$('.quote-line',form).map(row=>({name:$('[name="itemName"]',row).value,quantity:Number($('[name="quantity"]',row).value),unitPrice:Number($('[name="unitPrice"]',row).value)}));delete data.itemName;delete data.quantity;delete data.unitPrice;}
 const plural={customer:'customers',activity:'activities',quote:'quotes',task:'tasks'}[entity]; const btn=$('#save-button'); btn.disabled=true;btn.textContent='저장 중…';$('#form-error').hidden=true;
 try {await api(`/api/${plural}${id?'/'+id:''}`,{method:id?'PUT':'POST',body:JSON.stringify(data)});await refresh();closeModal();render();if(state.view==='reports') loadReport();toast('저장했습니다.');}
 catch(err) {$('#form-error').textContent=err.message;$('#form-error').hidden=false;btn.disabled=false;btn.textContent='다시 저장';}
}
function confirmDelete(entity,id) {
 const plural={customer:'customers',activity:'activities',quote:'quotes',task:'tasks'}[entity];const record=state.data[plural].find(r=>r.id===Number(id));if(!record)return;
 const label=record.name||record.title||record.content;
 openModal('이 기록을 삭제할까요?',`<div class="modal-body"><p><strong>${e(label)}</strong></p><p class="text-muted">삭제한 기록은 되돌릴 수 없습니다.${entity==='customer'?' 연결된 견적·영업활동·업무가 있는 고객사는 삭제할 수 없습니다.':''}</p><p id="delete-error" class="form-error" role="alert" hidden></p></div>`,`<div class="modal-footer">${button('취소','close-modal','secondary')}<button class="button danger" id="confirm-delete">삭제하기</button></div>`);
 $('#confirm-delete').onclick=async()=>{const btn=$('#confirm-delete');btn.disabled=true;try{await api(`/api/${plural}/${id}`,{method:'DELETE'});await refresh();closeModal();render();if(state.view==='reports')loadReport();toast('삭제했습니다.');}catch(err){$('#delete-error').textContent=err.message;$('#delete-error').hidden=false;btn.disabled=false;}};
}
async function toggleTask(input) {
 const t=state.data.tasks.find(t=>t.id===Number(input.dataset.taskId));if(!t)return;input.disabled=true;
 try {await api(`/api/tasks/${t.id}`,{method:'PUT',body:JSON.stringify({status:input.checked?'완료':'미완료'})});await refresh();render();toast(input.checked?'업무를 완료했습니다.':'업무를 미완료로 변경했습니다.');}catch(err){input.checked=!input.checked;input.disabled=false;toast(err.message,true);}
}
async function handleRestore(event) {
 const file=event.target.files[0];event.target.value='';if(!file)return;
 if(file.size>8*1024*1024) {toast('8MB 이하의 백업 파일을 선택해 주세요.',true);return;}
 let data;try{data=JSON.parse(await file.text());}catch{toast('올바른 JSON 백업 파일을 선택해 주세요.',true);return;}
 openModal('백업을 복원할까요?',`<div class="modal-body"><p><strong>${e(file.name)}</strong></p><p>현재 저장된 모든 데이터가 백업 내용으로 교체됩니다. 현재 데이터를 남기려면 먼저 백업을 다운로드해 주세요.</p><p id="restore-error" class="form-error" role="alert" hidden></p></div>`,`<div class="modal-footer">${button('취소','close-modal','secondary')}<button class="button danger" id="confirm-restore">데이터 교체 및 복원</button></div>`);
 $('#confirm-restore').onclick=async()=>{const btn=$('#confirm-restore');btn.disabled=true;btn.textContent='복원 중…';try{await api('/api/restore',{method:'POST',body:JSON.stringify(data)});await refresh();closeModal();render();toast('백업을 복원했습니다.');}catch(err){$('#restore-error').hidden=false;$('#restore-error').textContent=err.message;btn.disabled=false;btn.textContent='데이터 교체 및 복원';}};
}
async function download(path,fallbackName) {
 try {const res=await fetch(path);if(!res.ok){let msg='파일을 다운로드하지 못했습니다.';try{msg=(await res.json()).error||msg;}catch{}throw new Error(msg);}const blob=await res.blob();const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=fallbackName;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);toast('다운로드를 시작했습니다. 브라우저의 다운로드 목록을 확인하세요.');}catch(err){toast(err.message,true);}
}
document.addEventListener('click', event=>{
 const el=event.target.closest('[data-action]');if(!el)return;const action=el.dataset.action,id=el.dataset.id;
 if(action==='close-modal')return closeModal();
 if(action==='menu')return document.body.classList.add('menu-open');
 if(action==='close-menu')return document.body.classList.remove('menu-open');
 if(action==='customer-detail'){state.detail=Number(id);render();return;}
 if(action==='customer-list'){state.detail=null;render();return;}
 if(action==='detail-edit-customer')return editForm('customer',state.detail);
 if(action.startsWith('new-'))return editForm(action.slice(4));
 if(action.startsWith('edit-'))return editForm(action.slice(5),id);
 if(action.startsWith('delete-'))return confirmDelete(action.slice(7),id);
 if(action==='add-item'){if($$('.quote-line').length>=50){toast('견적 한 건에는 최대 50개 품목을 등록할 수 있습니다.',true);return;}$('#quote-lines').insertAdjacentHTML('beforeend',itemForm());return;}
 if(action==='remove-item'){if($$('.quote-line').length===1){toast('최소 한 개의 품목이 필요합니다.',true);return;}el.closest('.quote-line').remove();updateQuoteSum();return;}
 if(['prev-week','next-week','this-week'].includes(action)){state.week=action==='this-week'?monday(today()):shiftDate(state.week,action==='prev-week'?-7:7);state.report=null;$('#view-content').innerHTML=reportsView();bindViewInputs();loadReport();return;}
 if(action==='retry-report')return loadReport();
 if(action==='export-report')return download(`/api/report.xlsx?week=${state.week}`,`주간영업보고서_${state.week}.xlsx`);
 if(action==='backup')return download('/api/backup',`영업관리_백업_${today()}.json`);
 if(action==='restore-select')return $('#restore-file').click();
});
document.addEventListener('change',event=>{if(event.target.matches('[data-task-id]'))toggleTask(event.target);});
document.addEventListener('keydown',event=>{
 if(event.key==='Escape'){closeModal();document.body.classList.remove('menu-open');}
 if(event.key==='Tab'&&$('.modal')){const focusables=$$('button:not(:disabled), input:not([type="hidden"]), select, textarea, a[href]', $('.modal')).filter(el=>!el.hidden);const first=focusables[0],last=focusables.at(-1);if(event.shiftKey&&document.activeElement===first){event.preventDefault();last?.focus();}else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first?.focus();}}
});
window.addEventListener('hashchange',()=>{document.body.classList.remove('menu-open');closeModal();route();});
(async()=>{try{await refresh();route();}catch(err){$('#app').innerHTML=`<div class="empty-state"><h1>영업관리 시스템에 연결할 수 없습니다</h1><p>${e(err.message)}</p><p>실행 창을 확인한 뒤 브라우저를 새로고침해 주세요.</p><button class="button primary" onclick="location.reload()">다시 불러오기</button></div>`;}})();
