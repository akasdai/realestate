// ── 상태 ──────────────────────────────────────────────────────────────────────
const state = {
  regionCode: null,
  regionName: null,
  activeTab: 'apt',
  dealType: 'trade',
  allItems: [],
  lastData: null,
  complexMap: {},      // normalized_name → complex info
  complexAvail: null,  // null=미조회, true=사용가능, false=미승인
};

const M2_PER_PYEONG = 3.30579;

// ── DOM 참조 ──────────────────────────────────────────────────────────────────
const regionInput    = document.getElementById('region-input');
const regionBadge    = document.getElementById('region-badge');
const candidatesEl   = document.getElementById('region-candidates');
const yearMonthInput = document.getElementById('year-month-input');
const rowsInput      = document.getElementById('rows-input');
const searchBtn      = document.getElementById('search-btn');
const loadingEl      = document.getElementById('loading');
const errorEl        = document.getElementById('error-msg');
const summarySection = document.getElementById('summary-section');
const summaryGrid    = document.getElementById('summary-grid');
const resultSection  = document.getElementById('result-section');
const resultCount    = document.getElementById('result-count');
const resultThead    = document.getElementById('result-thead');
const resultTbody    = document.getElementById('result-tbody');
const dealTypeRow    = document.getElementById('deal-type-row');

// 기존 필터
const fAreaMin  = document.getElementById('f-area-min');
const fAreaMax  = document.getElementById('f-area-max');
const fPriceMin = document.getElementById('f-price-min');
const fPriceMax = document.getElementById('f-price-max');
const fFloorMin = document.getElementById('f-floor-min');
const fFloorMax = document.getElementById('f-floor-max');
const fYearMin  = document.getElementById('f-year-min');
const fYearMax  = document.getElementById('f-year-max');
const filterReset = document.getElementById('filter-reset');
const pyeongHint  = document.getElementById('pyeong-hint');
const fPriceLabel = document.getElementById('f-price-label');

// 단지정보 필터
const fUnitsMin  = document.getElementById('f-units-min');
const fUnitsMax  = document.getElementById('f-units-max');
const fParkingMin = document.getElementById('f-parking-min');
const fParkingMax = document.getElementById('f-parking-max');
const complexApiStatus = document.getElementById('complex-api-status');
const complexApiBadges = document.querySelectorAll('.complex-api-badge');

// ── 초기화 ────────────────────────────────────────────────────────────────────
function init() {
  const now = new Date();
  now.setMonth(now.getMonth() - 1);
  yearMonthInput.value = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;

  // 탭
  document.querySelectorAll('.tab').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
      btn.classList.add('active');
      state.activeTab = btn.dataset.tab;
      const isComplex = ['apt'].includes(state.activeTab);
      document.querySelectorAll('.complex-filter').forEach(el => {
        el.style.opacity = isComplex ? '1' : '.4';
        el.querySelectorAll('input,button').forEach(i => i.disabled = !isComplex);
      });
      if (state.activeTab === 'commercial') {
        dealTypeRow.style.visibility = 'hidden';
        state.dealType = 'trade';
        document.querySelector('input[name="deal-type"][value="trade"]').checked = true;
      } else {
        dealTypeRow.style.visibility = 'visible';
      }
      updatePriceLabel();
    });
  });

  // 거래유형 라디오
  document.querySelectorAll('input[name="deal-type"]').forEach(radio => {
    radio.addEventListener('change', () => { state.dealType = radio.value; updatePriceLabel(); });
  });

  // 지역명
  regionInput.addEventListener('keydown', e => { if (e.key === 'Enter') lookupRegion(); });
  regionInput.addEventListener('blur', () => {
    setTimeout(() => { if (!candidatesEl.matches(':hover')) lookupRegion(); }, 150);
  });
  regionInput.addEventListener('input', () => { if (!regionInput.value.trim()) clearRegion(); });

  searchBtn.addEventListener('click', doSearch);

  // 필터 입력 → rerender
  [fAreaMin, fAreaMax, fPriceMin, fPriceMax, fFloorMin, fFloorMax, fYearMin, fYearMax, fUnitsMin, fUnitsMax, fParkingMin, fParkingMax]
    .forEach(el => el.addEventListener('input', () => { if (el === fAreaMin || el === fAreaMax) updatePyeongHint(); rerender(); }));

  // 칩 클릭 설정
  setupChips('.pyeong-chips .chip',  'areaMin',    'areaMax',    fAreaMin,    fAreaMax,    () => updatePyeongHint());
  setupChips('.price-chips .chip',   'priceMin',   'priceMax',   fPriceMin,   fPriceMax);
  setupChips('.floor-chips .chip',   'floorMin',   'floorMax',   fFloorMin,   fFloorMax);
  setupChips('.year-chips .chip',    'yearMin',    'yearMax',    fYearMin,    fYearMax);
  setupChips('.units-chips .chip',   'unitsMin',   'unitsMax',   fUnitsMin,   fUnitsMax);
  setupChips('.parking-chips .chip', 'parkingMin', 'parkingMax', fParkingMin, fParkingMax);

  filterReset.addEventListener('click', resetFilters);
}

function setupChips(selector, minKey, maxKey, minEl, maxEl, onApply) {
  document.querySelectorAll(selector).forEach(chip => {
    chip.addEventListener('click', () => {
      const parent = chip.closest('div');
      parent.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
      chip.classList.toggle('active');
      if (chip.classList.contains('active')) {
        minEl.value = chip.dataset[minKey] ?? '';
        maxEl.value = chip.dataset[maxKey] ?? '';
      } else {
        minEl.value = '';
        maxEl.value = '';
      }
      if (onApply) onApply();
      rerender();
    });
  });
}

function resetFilters() {
  [fAreaMin, fAreaMax, fPriceMin, fPriceMax, fFloorMin, fFloorMax, fYearMin, fYearMax, fUnitsMin, fUnitsMax, fParkingMin, fParkingMax]
    .forEach(el => { el.value = ''; });
  document.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
  pyeongHint.textContent = '';
  rerender();
}

function updatePriceLabel() {
  fPriceLabel.textContent = state.dealType === 'rent' ? '보증금' : '거래금액';
}

function updatePyeongHint() {
  const min = parseFloat(fAreaMin.value);
  const max = parseFloat(fAreaMax.value);
  const parts = [];
  if (!isNaN(min)) parts.push(`${(min / M2_PER_PYEONG).toFixed(1)}평`);
  if (!isNaN(max)) parts.push(`${(max / M2_PER_PYEONG).toFixed(1)}평`);
  if (parts.length === 2) pyeongHint.textContent = `≈ ${parts[0]} ~ ${parts[1]}`;
  else if (!isNaN(min))   pyeongHint.textContent = `최소 ≈ ${parts[0]}`;
  else if (!isNaN(max))   pyeongHint.textContent = `최대 ≈ ${parts[0]}`;
  else pyeongHint.textContent = '';
}

// ── 단지정보 API 상태 표시 ────────────────────────────────────────────────────
function setComplexStatus(status, msg) {
  // status: 'loading' | 'ready' | 'pending' | 'error'
  complexApiStatus.className = 'complex-api-status ' + (status === 'loading' ? 'pending' : status);
  complexApiStatus.textContent = msg;

  complexApiBadges.forEach(b => {
    b.className = 'complex-api-badge';
    if (status === 'ready') b.classList.add('ready');
    if (status === 'error' || status === 'pending') b.classList.add('error');
  });
}

// ── 단지정보 정규화 ───────────────────────────────────────────────────────────
function normalizeName(name) {
  return (name || '').replace(/[\s\-_·]/g, '').toLowerCase();
}

function lookupComplex(name) {
  const norm = normalizeName(name);
  if (!norm) return null;
  if (state.complexMap[norm]) return state.complexMap[norm];
  // 부분 매칭
  for (const [key, val] of Object.entries(state.complexMap)) {
    if (norm.includes(key) || key.includes(norm)) return val;
  }
  return null;
}

// ── 지역코드 조회 ─────────────────────────────────────────────────────────────
async function lookupRegion() {
  const q = regionInput.value.trim();
  if (!q) { clearRegion(); return; }
  try {
    const res = await fetch(`/api/region?q=${encodeURIComponent(q)}`);
    const data = await res.json();
    if (data.code) { setRegion(data.name, data.code); showCandidates(data.candidates || []); }
    else { clearRegion(); showCandidates([]); }
  } catch { clearRegion(); }
}

function setRegion(name, code) {
  state.regionCode = code;
  state.regionName = name;
  regionBadge.textContent = `${name} (${code})`;
  regionBadge.classList.remove('hidden');
  searchBtn.disabled = false;
}

function clearRegion() {
  state.regionCode = null;
  state.regionName = null;
  regionBadge.classList.add('hidden');
  searchBtn.disabled = true;
  candidatesEl.classList.add('hidden');
}

function showCandidates(candidates) {
  if (!candidates || candidates.length <= 1) { candidatesEl.classList.add('hidden'); return; }
  candidatesEl.innerHTML = candidates.map(c =>
    `<div class="candidate-item" data-code="${c.code}" data-name="${c.name}">
      <span>${c.name}</span><span class="candidate-code">${c.code}</span>
    </div>`
  ).join('');
  candidatesEl.classList.remove('hidden');
  candidatesEl.querySelectorAll('.candidate-item').forEach(item => {
    item.addEventListener('mousedown', () => {
      regionInput.value = item.dataset.name;
      setRegion(item.dataset.name, item.dataset.code);
      candidatesEl.classList.add('hidden');
    });
  });
}

// ── 금액 포맷 ─────────────────────────────────────────────────────────────────
function formatAmount(manwon) {
  if (manwon == null || isNaN(manwon)) return '-';
  const uk = Math.floor(manwon / 10000);
  const rem = manwon % 10000;
  if (uk > 0 && rem > 0) return `${uk.toLocaleString()}억 ${rem.toLocaleString()}만`;
  if (uk > 0) return `${uk.toLocaleString()}억`;
  return `${manwon.toLocaleString()}만`;
}

// ── 필터 적용 ─────────────────────────────────────────────────────────────────
function getFilterValues() {
  return {
    areaMin:    parseFloat(fAreaMin.value)    || null,
    areaMax:    parseFloat(fAreaMax.value)    || null,
    priceMin:   parseFloat(fPriceMin.value)   || null,  // 억원
    priceMax:   parseFloat(fPriceMax.value)   || null,  // 억원
    floorMin:   parseInt(fFloorMin.value)     || null,
    floorMax:   parseInt(fFloorMax.value)     || null,
    yearMin:    parseInt(fYearMin.value)      || null,
    yearMax:    parseInt(fYearMax.value)      || null,
    unitsMin:   parseInt(fUnitsMin.value)     || null,
    unitsMax:   parseInt(fUnitsMax.value)     || null,
    parkingMin: parseInt(fParkingMin.value)   || null,
    parkingMax: parseInt(fParkingMax.value)   || null,
  };
}

function isFilterActive(f) {
  return Object.values(f).some(v => v != null);
}

function applyFilters(items) {
  const f = getFilterValues();
  if (!isFilterActive(f)) return items;

  return items.filter(item => {
    const area  = parseFloat(item.area_m2) || parseFloat(item.land_area_m2) || null;
    const price = state.dealType === 'trade' ? item.amount : item.deposit;
    const floor = parseInt(item.floor || item.floor_count) || null;
    const year  = parseInt(item.build_year || item._complex_year) || null;

    if (f.areaMin  != null && (area  == null || area  < f.areaMin))          return false;
    if (f.areaMax  != null && (area  == null || area  > f.areaMax))          return false;
    if (f.priceMin != null && (price == null || price < f.priceMin * 10000)) return false;
    if (f.priceMax != null && (price == null || price > f.priceMax * 10000)) return false;
    if (f.floorMin != null && (floor == null || floor < f.floorMin))         return false;
    if (f.floorMax != null && (floor == null || floor > f.floorMax))         return false;
    if (f.yearMin  != null && (year  == null || year  < f.yearMin))          return false;
    if (f.yearMax  != null && (year  == null || year  > f.yearMax))          return false;

    // 단지정보 필터 (단지 매칭된 경우만)
    const cx = item._complex;
    if (f.unitsMin  != null || f.unitsMax  != null) {
      const units = cx?.units ?? null;
      if (f.unitsMin  != null && (units == null || units < f.unitsMin))  return false;
      if (f.unitsMax  != null && (units == null || units > f.unitsMax))  return false;
    }
    if (f.parkingMin != null || f.parkingMax != null) {
      const parking = cx?.parking ?? null;
      if (f.parkingMin != null && (parking == null || parking < f.parkingMin)) return false;
      if (f.parkingMax != null && (parking == null || parking > f.parkingMax)) return false;
    }

    return true;
  });
}

// ── 통계 계산 ─────────────────────────────────────────────────────────────────
function calcMedian(arr) {
  if (!arr.length) return null;
  const s = [...arr].sort((a, b) => a - b);
  const m = Math.floor(s.length / 2);
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
}

function calcTradeSummary(items) {
  const amounts = items.map(i => i.amount).filter(a => typeof a === 'number' && a > 0);
  if (!amounts.length) return null;
  return { count: amounts.length, median: calcMedian(amounts), min: Math.min(...amounts), max: Math.max(...amounts) };
}

function calcRentSummary(items) {
  const jeonseD  = items.filter(i => i.rent_type === '전세').map(i => i.deposit).filter(Boolean);
  const monthlyD = items.filter(i => i.rent_type === '월세').map(i => i.deposit).filter(Boolean);
  const monthlyR = items.map(i => i.monthly_rent).filter(r => r && r > 0);
  const result = {};
  if (jeonseD.length)  result['전세_보증금_만원']   = { median: calcMedian(jeonseD),  count: jeonseD.length };
  if (monthlyD.length) result['월세_보증금_만원']   = { median: calcMedian(monthlyD), count: monthlyD.length };
  if (monthlyR.length) result['월세_월임대료_만원'] = { median: calcMedian(monthlyR), count: monthlyR.length };
  return result;
}

// ── 조회 실행 ─────────────────────────────────────────────────────────────────
async function doSearch() {
  if (!state.regionCode) return;
  const yearMonth = yearMonthInput.value.replace('-', '');
  const rows = rowsInput.value;

  setLoading(true);
  hideResults();
  state.complexMap = {};
  state.complexAvail = null;

  try {
    const endpoint = state.dealType === 'trade' ? '/api/trades' : '/api/rent';
    const tradeUrl   = `${endpoint}?type=${state.activeTab}&region_code=${state.regionCode}&year_month=${yearMonth}&rows=${rows}`;
    const complexUrl = `/api/complex?region_code=${state.regionCode}`;

    // 1단계: 거래 데이터 먼저 조회
    const isApt = state.activeTab === 'apt';
    const tradeData = await fetch(tradeUrl).then(r => r.json());
    if (tradeData.error) { showError(tradeData.error); return; }

    // 2단계: 아파트일 때 거래 결과의 단지명 추출 → 단지정보 병렬 조회
    if (isApt) {
      const aptNames = [...new Set(
        (tradeData.items || []).map(i => i.apt_name).filter(Boolean)
      )];
      const namesParam = encodeURIComponent(aptNames.join(','));
      const complexFullUrl = `${complexUrl}&apt_names=${namesParam}`;

      setComplexStatus('loading', '단지정보 조회 중...');
      try {
        const complexData = await fetch(complexFullUrl).then(r => r.json());
        if (complexData.error && complexData.matched_count === 0) {
          setComplexStatus('pending', '⚠ ' + complexData.error);
          state.complexAvail = false;
        } else if (complexData.complex_map && complexData.matched_count > 0) {
          state.complexMap = complexData.complex_map;
          setComplexStatus('ready', `✓ 단지정보 연동 완료 (${complexData.matched_count}개 단지 매칭)`);
          state.complexAvail = true;
        } else {
          setComplexStatus('pending', '단지정보 매칭 결과 없음');
          state.complexAvail = false;
        }
      } catch {
        setComplexStatus('error', '단지정보 조회 실패');
        state.complexAvail = false;
      }
    }

    // 거래 items에 단지정보 조인
    state.allItems = (tradeData.items || []).map(item => {
      const name = item.apt_name || item.offi_name || item.house_name || '';
      const cx = lookupComplex(name);
      return { ...item, _complex: cx || null };
    });
    state.lastData = tradeData;
    rerender();
  } catch (e) {
    showError('네트워크 오류: ' + e.message);
  } finally {
    setLoading(false);
  }
}

// ── rerender ─────────────────────────────────────────────────────────────────
function rerender() {
  if (!state.lastData) return;

  const filtered = applyFilters(state.allItems);
  const total    = state.lastData.total_count || state.allItems.length;
  const f        = getFilterValues();
  const active   = isFilterActive(f);

  // 요약 카드
  summaryGrid.innerHTML = '';
  const countLabel = active
    ? `${filtered.length.toLocaleString()} / ${state.allItems.length.toLocaleString()}`
    : filtered.length.toLocaleString();
  summaryGrid.appendChild(makeCard('조회 건수', countLabel, '건'));

  if (state.dealType === 'trade') {
    const s = calcTradeSummary(filtered);
    if (s) {
      summaryGrid.appendChild(makeCard('중앙값', formatAmount(s.median), '원'));
      summaryGrid.appendChild(makeCard('최솟값', formatAmount(s.min), '원'));
      summaryGrid.appendChild(makeCard('최댓값', formatAmount(s.max), '원'));
    }
  } else {
    const rs = calcRentSummary(filtered);
    if (rs['전세_보증금_만원'])   summaryGrid.appendChild(makeCard('전세 중앙값', formatAmount(rs['전세_보증금_만원'].median), '원'));
    if (rs['월세_보증금_만원'])   summaryGrid.appendChild(makeCard('월세 보증금', formatAmount(rs['월세_보증금_만원'].median), '원'));
    if (rs['월세_월임대료_만원']) summaryGrid.appendChild(makeCard('월세 중앙값', formatAmount(rs['월세_월임대료_만원'].median) + '/월', ''));
  }
  summarySection.classList.remove('hidden');

  const badge = active ? `<span class="filter-active-badge">필터 적용</span>` : '';
  resultCount.innerHTML = `${filtered.length.toLocaleString()}건 표시 (전체 ${total.toLocaleString()}건)${badge}`;

  if (state.dealType === 'trade') renderTradeTable(filtered);
  else renderRentTable(filtered);

  resultSection.classList.remove('hidden');
}

// ── 렌더링 ────────────────────────────────────────────────────────────────────
function makeCard(label, value, unit) {
  const div = document.createElement('div');
  div.className = 'summary-card';
  div.innerHTML = `<div class="label">${label}</div><div class="value">${value}</div>${unit ? `<div class="unit">${unit}</div>` : ''}`;
  return div;
}

function getBuildingName(item) {
  return item.apt_name || item.offi_name || item.house_name || item.house_type || item.use_type || '-';
}

function areaCell(item) {
  const m2 = item.area_m2 || item.land_area_m2;
  if (!m2) return '-';
  const p = (parseFloat(m2) / M2_PER_PYEONG).toFixed(1);
  return `${m2}<small style="color:var(--text-2)"> (≈${p}평)</small>`;
}

function complexCell(item) {
  const cx = item._complex;
  if (!cx) return '';
  const units   = cx.units   != null ? `${cx.units.toLocaleString()}세대` : null;
  const parking = cx.parking != null ? `주차 ${cx.parking.toLocaleString()}대` : null;
  const parts   = [units, parking].filter(Boolean);
  return parts.length ? `<div class="complex-info">${parts.join(' · ')}</div>` : '';
}

function renderTradeTable(items) {
  const hasComplex = state.complexAvail && items.some(i => i._complex);
  resultThead.innerHTML = `<tr>
    <th>건물명</th><th>법정동</th><th>거래금액</th>
    <th>면적(㎡)</th><th>층</th><th>건축년도</th>
    <th>거래일</th><th>거래유형</th>
    ${hasComplex ? '<th>세대수·주차</th>' : ''}
  </tr>`;
  resultTbody.innerHTML = items.map(item => `<tr>
    <td>${getBuildingName(item)}</td>
    <td>${item.dong || '-'}</td>
    <td class="amount-cell">${formatAmount(item.amount)}<br>
      <small style="color:var(--text-2);font-weight:400">${item.amount_raw || ''}</small></td>
    <td>${areaCell(item)}</td>
    <td>${item.floor || item.floor_count || '-'}</td>
    <td>${item.build_year || '-'}</td>
    <td>${item.deal_date || '-'}</td>
    <td>${item.deal_type || '-'}</td>
    ${hasComplex ? `<td>${complexCell(item)}</td>` : ''}
  </tr>`).join('');
}

function renderRentTable(items) {
  const hasComplex = state.complexAvail && items.some(i => i._complex);
  resultThead.innerHTML = `<tr>
    <th>건물명</th><th>법정동</th><th>유형</th>
    <th>보증금</th><th>월세</th><th>면적(㎡)</th>
    <th>층</th><th>거래일</th>
    ${hasComplex ? '<th>세대수·주차</th>' : ''}
  </tr>`;
  resultTbody.innerHTML = items.map(item => {
    const isJeonse = item.rent_type === '전세';
    const tag     = isJeonse ? '<span class="tag tag-jeonse">전세</span>' : '<span class="tag tag-monthly">월세</span>';
    const monthly = item.monthly_rent ? `<span class="monthly-cell">${formatAmount(item.monthly_rent)}/월</span>` : '-';
    return `<tr>
      <td>${getBuildingName(item)}</td>
      <td>${item.dong || '-'}</td>
      <td>${tag}</td>
      <td><span class="deposit-cell">${formatAmount(item.deposit)}</span></td>
      <td>${monthly}</td>
      <td>${areaCell(item)}</td>
      <td>${item.floor || '-'}</td>
      <td>${item.deal_date || '-'}</td>
      ${hasComplex ? `<td>${complexCell(item)}</td>` : ''}
    </tr>`;
  }).join('');
}

// ── UI 헬퍼 ──────────────────────────────────────────────────────────────────
function setLoading(on) {
  loadingEl.classList.toggle('hidden', !on);
  errorEl.classList.add('hidden');
}
function showError(msg) { errorEl.textContent = msg; errorEl.classList.remove('hidden'); }
function hideResults() { summarySection.classList.add('hidden'); resultSection.classList.add('hidden'); }

// ── CSS 추가 (complex-info) ───────────────────────────────────────────────────
const style = document.createElement('style');
style.textContent = `.complex-info{font-size:.75rem;color:var(--text-2);margin-top:.15rem}`;
document.head.appendChild(style);

// ── 시작 ──────────────────────────────────────────────────────────────────────
init();
