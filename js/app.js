(function () {
  'use strict';
  const $ = id => document.getElementById(id);
  const F = window.Charts.fmt;
  const esc = s => String(s === undefined || s === null ? '' : s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const C = { sun: '#ffd24d', panel: '#4c7de8', req: '#ff7a45', bat: '#5cff9d', alt: '#4dd8ff', waste: '#ff5d73', bus: '#c79bff' };
  const MASS = ['#8a9bc9', '#4c7de8', '#7ce0c3', '#5cff9d', '#ff7a45', '#c79bff', '#ffd24d'];
  let worker, rid = 0; const pend = new Map();
  let presets = null, schema = null, cfg = null, copter = null, last = null, sized = null, timer = null, seq = 0, view3d = false;

  function call(fn, ...args) { return new Promise((res, rej) => { const id = ++rid; pend.set(id, { res, rej }); worker.postMessage({ id, fn, args }); }); }
  const busy = (on, t) => { $('busy').style.display = on ? 'block' : 'none'; if (t) $('busyTxt').textContent = t; };
  const get = (o, p) => p.split('.').reduce((a, k) => (a == null ? undefined : a[k]), o);
  const set = (o, p, v) => { const ks = p.split('.'); let a = o; ks.slice(0, -1).forEach(k => { if (a[k] == null) a[k] = {}; a = a[k]; }); a[ks[ks.length - 1]] = v; };

  async function boot() {
    worker = new Worker('js/worker.js');
    worker.onmessage = e => { const m = e.data; if (m.type === 'progress') { $('bootTxt').textContent = m.text; return; } const p = pend.get(m.id); if (!p) return; pend.delete(m.id); m.ok ? p.res(m.data) : p.rej(new Error(m.error)); };
    const base = location.href.replace(/[^/]*$/, '');
    const ver = await new Promise((res, rej) => { const id = ++rid; pend.set(id, { res, rej }); worker.postMessage({ id, fn: 'boot', base }); });
    presets = await call('presets'); schema = await call('schema');
    copter = JSON.parse(JSON.stringify(presets.copter));
    $('preset').innerHTML = presets.planes.map(p => '<option value="' + p.id + '">' + esc(p.name) + '</option>').join('');
    $('preset').addEventListener('change', () => loadPreset($('preset').value));
    document.querySelectorAll('.tab').forEach(t => t.addEventListener('click', () => openTab(t.dataset.t)));
    $('btnExport').addEventListener('click', () => dl('solaris_config.json', JSON.stringify(cfg, null, 1)));
    $('btnImport').addEventListener('click', () => $('fileIn').click());
    $('fileIn').addEventListener('change', e => { const f = e.target.files[0]; if (!f) return; const r = new FileReader(); r.onload = () => { try { cfg = JSON.parse(r.result); renderForm(); schedule(0); } catch (err) { alert(err.message); } }; r.readAsText(f); e.target.value = ''; });
    $('dRun').addEventListener('click', runSpace); $('mRun').addEventListener('click', runSeason);
    $('sRun').addEventListener('click', runSize); $('sApply').addEventListener('click', () => { if (!sized) return; cfg = JSON.parse(JSON.stringify(sized.config)); renderForm(); schedule(0); $('sApply').disabled = true; });
    $('cRun').addEventListener('click', runCopter); $('vRun').addEventListener('click', runVal);
    renderCopterForm(); about(ver.version);
    $('boot').style.display = 'none';
    loadPreset(presets.planes[0].id);
  }

  function loadPreset(id) { const p = presets.planes.find(x => x.id === id); cfg = JSON.parse(JSON.stringify(p.config)); $('pdesc').textContent = p.description; renderForm(); schedule(0); spaceDefaults(); }
  function spaceDefaults() { const b = cfg.airframe.span_m, m = cfg.battery.mass_kg; $('dS0').value = +(b * 0.4).toFixed(2); $('dS1').value = +(b * 1.8).toFixed(2); $('dB0').value = +(m * 0.2).toFixed(2); $('dB1').value = +(m * 2.5).toFixed(2); }

  function field(f, obj) {
    const v = get(obj, f.path);
    if (f.type === 'bool') return '<div class="fld"><label>' + esc(f.label) + '</label><select data-p="' + f.path + '" data-b="1"><option value="1"' + (v ? ' selected' : '') + '>yes</option><option value="0"' + (!v ? ' selected' : '') + '>no</option></select><span class="u"></span></div>';
    return '<div class="fld"><label>' + esc(f.label) + '</label><input type="number" step="' + (f.step || 'any') + '" data-p="' + f.path + '" value="' + (v == null ? '' : v) + '"><span class="u">' + esc(f.unit || '') + '</span></div>';
  }
  function renderForm() {
    $('form').innerHTML = schema.groups.map(g => '<div class="grp"><h3>' + esc(g.label) + '<span>▾</span></h3><div class="body">' + g.fields.map(f => field(f, cfg)).join('') + '</div></div>').join('');
    $('form').querySelectorAll('.grp h3').forEach(h => h.addEventListener('click', () => h.parentElement.classList.toggle('closed')));
    $('form').querySelectorAll('[data-p]').forEach(el => el.addEventListener('change', () => { let v; if (el.dataset.b) v = el.value === '1'; else { v = Number(el.value); if (!Number.isFinite(v)) return; } set(cfg, el.dataset.p, v); schedule(); }));
  }
  function renderCopterForm() {
    $('cForm').innerHTML = schema.copter.map(f => field(f, copter)).join('');
    $('cForm').querySelectorAll('[data-p]').forEach(el => el.addEventListener('change', () => { const v = Number(el.value); if (Number.isFinite(v)) { copter[el.dataset.p] = v; runCopter(); } }));
  }

  function schedule(ms) { clearTimeout(timer); timer = setTimeout(run, ms === undefined ? 250 : ms); }
  async function run() {
    const s = ++seq; busy(true, 'Flying day and night …');
    try {
      const r = await call('run', JSON.stringify(cfg)); if (s !== seq) return;
      last = r; kpis(); mission(); mass();
      if (view3d) window.SolScene.load(last);
    } catch (e) { $('flags').textContent = 'Error: ' + e.message; } finally { if (s === seq) busy(false); }
  }

  function kpis() {
    const s = last.summary, solar = cfg.solar.enabled !== false && s.panel_area_m2 > 0;
    const verdict = solar ? (s.perpetual ? 'PERPETUAL' : s.survives ? 'NOT SUSTAINED' : 'BATTERY EMPTY') : 'ENDURANCE';
    const ok = s.perpetual || (!solar && s.endurance_h);
    const it = [
      ['Verdict', '<span class="pill ' + (s.perpetual ? 'ok' : 'bad') + '">' + verdict + '</span>', solar ? 'day ' + cfg.mission.day_of_year + ' · ' + cfg.mission.latitude_deg + '°' : 'battery only'],
      [solar ? 'Night margin' : 'Endurance', solar ? (s.night_margin * 100).toFixed(1) + ' %' : (s.endurance_h ? s.endurance_h.toFixed(2) + ' h' : '> ' + cfg.mission.days * 24 + ' h'), solar ? 'lowest SOC above reserve' : 'until minimum SOC'],
      ['Excess time', solar ? s.excess_time_h.toFixed(1) + ' h/day' : '–', 'battery full, sun still up'],
      ['Mass', F(s.mass_kg, s.mass_kg < 10 ? 2 : 1) + ' kg', 'wing loading ' + F(s.wing_loading, 1) + ' N/m²'],
      ['Span', F(s.span_m, 1) + ' m', F(s.wing_area_m2, 2) + ' m² wing'],
      ['Level-flight power', F(s.p_level_w, 0) + ' W', 'at ' + F(s.v_cruise_mps, 1) + ' m/s · L/D ' + F(s.ld, 1)],
      ['Solar peak', solar ? F(s.p_peak_w, 0) + ' W' : '–', solar ? F(s.panel_area_m2, 2) + ' m² cells' : 'no cells'],
    ];
    $('kpis').innerHTML = it.map(k => '<div class="kpi"><span>' + k[0] + '</span><b>' + k[1] + '</b><small>' + esc(k[2]) + '</small></div>').join('');
    $('flags').textContent = !ok && solar ? '⚠ ' + (s.survives ? 'The battery survives the night, but the daily energy balance is negative – flight is not sustainable.' : 'The battery reaches its minimum state of charge – more battery, more cells or a lighter design is needed.') : '';
  }

  function nightBands(S) { const out = []; let st = null; S.irr.forEach((v, i) => { if (v <= 0 && st === null) st = i; if ((v > 0 || i === S.irr.length - 1) && st !== null) { out.push({ x0: S.t_h[st], x1: S.t_h[i], color: 'rgba(40,60,140,.18)', label: S.t_h[i] - S.t_h[st] > 3 ? 'night' : '' }); st = null; } }); return out; }

  function mission() {
    const S = last.series; if (!S) return;
    const t = S.t_h, b = nightBands(S);
    Charts.line($('cPow'), { series: [{ x: t, y: S.p_solar, name: 'solar power [W]', color: C.sun, area: true }, { x: t, y: S.p_req, name: 'required power [W]', color: C.req }, { x: t, y: S.p_waste, name: 'curtailed [W]', color: C.waste, width: 1.2, dash: true }], xlabel: 'time since start [h]', ylabel: 'power [W]', bands: b, height: 270 });
    Charts.line($('cSoc'), { series: [{ x: t, y: S.soc.map(v => v * 100), name: 'state of charge [%]', color: C.bat, area: true }, { x: [t[0], t[t.length - 1]], y: [cfg.battery.soc_min * 100, cfg.battery.soc_min * 100], name: 'reserve', color: C.waste, dash: true, width: 1.2 }], xlabel: 'time [h]', ylabel: 'SOC [%]', bands: b, ymin: Math.min(0, ...S.soc.map(v => v * 100)) });
    Charts.line($('cAlt'), { series: [{ x: t, y: S.alt, name: 'altitude [m]', color: C.alt, area: true }], xlabel: 'time [h]', ylabel: 'altitude [m]', bands: b, ymin: Math.min(...S.alt) * 0.98 });
    Charts.line($('cIrr'), { series: [{ x: t, y: S.irr, name: 'irradiance [W/m²]', color: C.sun, area: true }, { x: t, y: S.sun_el, name: 'sun elevation [°]', color: C.panel, axis: 2 }], xlabel: 'time [h]', ylabel: 'irradiance [W/m²]', y2: 'sun elevation [°]', y2min: -90, bands: b });
    const s = last.summary, d = Math.max(1, cfg.mission.days);
    const rows = [['Solar energy harvested', s.e_solar_kwh / d, C.sun], ['Consumed (propulsion + systems)', s.e_used_kwh / d, C.req], ['Stored into battery', s.e_bat_in_kwh / d, C.bat], ['Drawn from battery', s.e_bat_out_kwh / d, C.bus], ['Curtailed (battery full)', s.e_waste_kwh / d, C.waste]];
    const mx = Math.max(...rows.map(r => r[1]), 1e-9);
    $('eBud').innerHTML = rows.map(r => '<div style="margin:8px 0"><div class="row" style="justify-content:space-between"><span class="sub">' + r[0] + '</span><b>' + F(r[1] * 1000, 0) + ' Wh/day</b></div><div class="bar" style="height:10px"><div style="width:' + (r[1] / mx * 100) + '%;background:' + r[2] + '"></div></div></div>').join('') + '<div class="desc" style="margin-top:10px">Extraterrestrial irradiation on a horizontal surface: ' + F(s.daily_irradiation_kwhm2, 2) + ' kWh/m² per day</div>';
  }

  function mass() {
    Charts.donut($('cMass'), last.mass, MASS);
    const s = last.summary;
    const rows = [['Wing area', F(s.wing_area_m2, 2) + ' m²'], ['Solar cell area', F(s.panel_area_m2, 2) + ' m²'], ['Battery energy', F(s.battery_wh, 0) + ' Wh'], ['Cruise speed', F(s.v_cruise_mps, 1) + ' m/s (' + F(s.v_cruise_mps * 3.6, 0) + ' km/h)'], ['Lift coefficient', F(s.cl_cruise, 2)], ['Lift-to-drag ratio', F(s.ld, 1)], ['Level-flight power', F(s.p_level_w, 1) + ' W'], ['Power-to-weight', F(s.p_level_w / s.mass_kg, 1) + ' W/kg']];
    $('tKey').innerHTML = '<table>' + rows.map(r => '<tr><td class="sub">' + r[0] + '</td><td class="n"><b>' + r[1] + '</b></td></tr>').join('') + '</table>';
  }

  function openTab(t) {
    document.querySelectorAll('.tab').forEach(x => x.classList.toggle('on', x.dataset.t === t));
    document.querySelectorAll('.pane').forEach(x => x.classList.toggle('on', x.id === 'p-' + t));
    if (t === 'flight') start3d();
    if (t === 'mission' && last) mission();
    if (t === 'mass' && last) mass();
    if (t === 'copter' && !$('cCop').innerHTML) runCopter();
  }

  function start3d() {
    if (!view3d) {
      view3d = window.SolScene.init($('v3')); if (!view3d) return;
      window.SolScene.onFrame = hud; window.SolScene.onEnd = () => { $('bPlay').textContent = '▶ Play'; };
      $('bPlay').addEventListener('click', () => { if (window.SolScene.isPlaying()) { window.SolScene.pause(); $('bPlay').textContent = '▶ Play'; } else { window.SolScene.play(); $('bPlay').textContent = '❚❚ Pause'; } });
      $('bSpeed').addEventListener('change', e => window.SolScene.setSpeed(+e.target.value));
      $('bSeek').addEventListener('input', e => window.SolScene.seek(e.target.value / 1000));
      if (last) window.SolScene.load(last);
      setTimeout(() => { window.SolScene.resize(); window.SolScene.play(); $('bPlay').textContent = '❚❚ Pause'; }, 60);
    } else window.SolScene.resize();
  }
  function hud(i, th) {
    const S = last.series; const hr = S.hour[i], hh = Math.floor(hr), mm = Math.floor((hr - hh) * 60);
    const mode = { level: 'LEVEL FLIGHT', climb: 'CLIMBING ON SURPLUS', glide: 'GLIDING (altitude storage)' }[S.mode[i]];
    $('hud').innerHTML = '<div style="font-weight:800;color:#fff;margin-bottom:4px">' + (S.irr[i] > 0 ? '☀ ' : '☾ ') + String(hh).padStart(2, '0') + ':' + String(mm).padStart(2, '0') + ' solar time · day ' + (Math.floor(th / 24) + 1) + '</div><div class="r"><span>mode</span><b>' + mode + '</b></div><div class="r"><span>sun elevation</span><b>' + S.sun_el[i].toFixed(1) + '°</b></div><div class="r"><span>irradiance</span><b style="color:' + C.sun + '">' + S.irr[i].toFixed(0) + ' W/m²</b></div><div class="r"><span>solar power</span><b style="color:' + C.sun + '">' + S.p_solar[i].toFixed(1) + ' W</b></div><div class="r"><span>required power</span><b style="color:' + C.req + '">' + S.p_req[i].toFixed(1) + ' W</b></div><div class="r"><span>altitude</span><b style="color:' + C.alt + '">' + S.alt[i].toFixed(0) + ' m</b></div><div class="r"><span>battery</span><b style="color:' + C.bat + '">' + (S.soc[i] * 100).toFixed(1) + ' %</b></div><div class="bar"><div style="width:' + Math.max(0, Math.min(100, S.soc[i] * 100)) + '%;background:' + (S.soc[i] > 0.3 ? C.bat : S.soc[i] > 0.1 ? C.sun : C.waste) + '"></div></div>';
    $('bSeek').value = Math.round(window.SolScene.progress() * 1000);
    $('bTime').textContent = th.toFixed(1) + ' / ' + S.t_h[S.t_h.length - 1].toFixed(0) + ' h';
  }

  async function runSpace() {
    busy(true, 'Mapping the design space …');
    try {
      const r = await call('design_space', JSON.stringify(cfg), +$('dS0').value, +$('dS1').value, +$('dB0').value, +$('dB1').value, +$('dN').value);
      Charts.heat($('cSpace'), { x: r.x, y: r.y, z: r.z, xlabel: 'wingspan [m]', ylabel: 'battery mass [kg]', height: 420 });
    } catch (e) { $('cSpace').textContent = e.message; } finally { busy(false); }
  }
  async function runSeason() {
    busy(true, 'Flying a whole year at 15 latitudes …');
    try {
      const r = await call('season_map', JSON.stringify(cfg));
      const mon = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
      Charts.heat($('cSeason'), { x: r.x, y: r.y, z: r.z, xlabel: 'day of year', ylabel: 'latitude [°N]', height: 420, xfmt: d => mon[Math.min(11, Math.floor((d - 1) / 30.5))] });
    } catch (e) { $('cSeason').textContent = e.message; } finally { busy(false); }
  }
  async function runSize() {
    busy(true, 'Sizing loop …');
    try {
      const r = await call('size', JSON.stringify(cfg)); sized = r.ok ? r : null;
      $('sOut').innerHTML = r.ok ? '<div class="kpis"><div class="kpi"><span>Minimum span</span><b>' + F(r.span_m, 2) + ' m</b><small>for perpetual flight</small></div><div class="kpi"><span>Optimal battery</span><b>' + F(r.battery_kg, 2) + ' kg</b><small>' + F(r.result.summary.battery_wh, 0) + ' Wh</small></div><div class="kpi"><span>Total mass</span><b>' + F(r.result.summary.mass_kg, 2) + ' kg</b><small>night margin ' + (r.result.summary.night_margin * 100).toFixed(1) + ' %</small></div></div>' : '<span class="fail">' + esc(r.reason) + '</span>';
      $('sApply').disabled = !r.ok;
    } catch (e) { $('sOut').textContent = e.message; } finally { busy(false); }
  }
  async function runCopter() {
    try {
      const r = await call('copter', JSON.stringify(copter));
      $('cKpi').innerHTML = '<div class="kpis"><div class="kpi"><span>Hover</span><b>' + F(r.hover_min, 1) + ' min</b><small>' + F(r.hover_w, 0) + ' W</small></div><div class="kpi"><span>Max. endurance</span><b>' + F(r.best_endurance.endurance_min, 1) + ' min</b><small>at ' + F(r.best_endurance.v, 1) + ' m/s</small></div><div class="kpi"><span>Max. range</span><b>' + F(r.best_range.range_km, 1) + ' km</b><small>at ' + F(r.best_range.v, 1) + ' m/s</small></div><div class="kpi"><span>Disk loading</span><b>' + F(r.disk_loading, 0) + '</b><small>N/m² · ' + F(r.mass_kg, 2) + ' kg</small></div></div>';
      const v = r.curve.map(p => p.v);
      Charts.line($('cCop'), { series: [{ x: v, y: r.curve.map(p => p.p), name: 'power [W]', color: C.req }, { x: v, y: r.curve.map(p => p.range_km), name: 'range [km]', color: C.alt, axis: 2 }], xlabel: 'airspeed [m/s]', ylabel: 'electrical power [W]', y2: 'range [km]', height: 300 });
      Charts.line($('cPay'), { series: [{ x: r.payload.map(p => p.payload_kg), y: r.payload.map(p => p.hover_min), name: 'hover endurance [min]', color: C.bat, area: true, dots: true }], xlabel: 'payload [kg]', ylabel: 'endurance [min]' });
    } catch (e) { $('cKpi').textContent = e.message; }
  }
  async function runVal() {
    busy(true, 'Validation …'); const t0 = performance.now();
    try {
      const r = await call('validate'); const ok = r.filter(x => x.ok).length;
      $('vOut').innerHTML = '<div class="kpis"><div class="kpi"><span>Checks passed</span><b class="' + (ok === r.length ? 'pass' : 'fail') + '">' + ok + ' / ' + r.length + '</b><small>Python engine in your browser</small></div><div class="kpi"><span>Run time</span><b>' + ((performance.now() - t0) / 1000).toFixed(1) + ' s</b></div></div><table><tr><th>Group</th><th>Check</th><th>Result</th><th>Detail</th><th>Reference</th></tr>' + r.map(x => '<tr><td>' + esc(x.group) + '</td><td>' + esc(x.name) + '</td><td class="' + (x.ok ? 'pass' : 'fail') + '">' + (x.ok ? 'PASS' : 'FAIL') + '</td><td>' + esc(x.detail) + '</td><td class="sub">' + esc(x.ref) + '</td></tr>').join('') + '</table>';
    } catch (e) { $('vOut').textContent = e.message; } finally { busy(false); }
  }
  function about(v) {
    $('about').innerHTML = '<h2>Model</h2><p class="desc">All physics runs in the Python package <code>solaris</code> (Pyodide ' + esc(v) + ', background worker).</p><table>' + [
      ['Sun', 'Declination (Cooper), hour angle, elevation and azimuth; extraterrestrial irradiance with orbit eccentricity'],
      ['Irradiance', 'Air mass (Kasten–Young) scaled with pressure at flight altitude, direct beam 0.7^(AM^0.678) plus diffuse share, sky clearness factor'],
      ['Atmosphere', 'ISA up to 32 km (troposphere, tropopause, lower stratosphere)'],
      ['Flight', 'Level flight at the minimum-power lift coefficient √(3·CD0/k), limited to 90 % of CL max'],
      ['Mass', 'Structure from the solar-aircraft regression of Noth (ETH Zurich) or fixed; solar cells per m², MPPT per W, propulsion per W with power margin, battery from mass'],
      ['Energy', 'Time-stepped day/night balance: solar → load → battery (charge/discharge efficiency, C-rate limit) → curtailment; optional altitude storage (climb on surplus, glide at night)'],
      ['Perpetual flight', 'Battery never below its reserve and the state of charge at the same solar time does not fall from one day to the next'],
      ['Multicopter', 'Momentum theory with figure of merit, Glauert induced velocity in forward flight, parasite drag'],
    ].map(r => '<tr><td style="width:160px;color:#fff;font-weight:600">' + r[0] + '</td><td class="sub">' + r[1] + '</td></tr>').join('') + '</table><p class="desc" style="margin-top:12px">Conceptual-design accuracy for comparing configurations – not certified performance data.</p>';
  }
  function dl(n, t) { const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([t], { type: 'application/json' })); a.download = n; document.body.appendChild(a); a.click(); setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 400); }
  window.addEventListener('resize', () => { if (last && document.querySelector('.tab.on').dataset.t === 'mission') mission(); });
  window.SolApp = { get cfg() { return cfg; }, get last() { return last; }, openTab };
  boot().catch(e => { $('bootTxt').textContent = 'Could not start the Python engine: ' + e.message; });
})();
