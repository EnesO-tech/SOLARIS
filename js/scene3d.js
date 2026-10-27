(function () {
  'use strict';
  let renderer, scene, camera, controls, host, clock, sunLight, hemi, sunMesh, sunGlow, stars, ground, plane, props = [], flows = [], rays, batMesh;
  let data = null, playing = false, speed = 1800, simT = 0, idx = 0, onFrame = null, ready = false, peakSun = 1, peakReq = 1, orbitR = 26;
  let DAY, DUSK, NIGHT;

  function init(el) {
    host = el;
    if (!window.THREE) { el.innerHTML = '<div class="nogl">3D needs three.js – check the internet connection and reload.</div>'; return false; }
    DAY = new THREE.Color(0x3d7fd6); DUSK = new THREE.Color(0xe0784a); NIGHT = new THREE.Color(0x050914);
    renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setPixelRatio(window.devicePixelRatio || 1);
    el.appendChild(renderer.domElement);
    scene = new THREE.Scene();
    scene.fog = new THREE.Fog(0x050914, 120, 420);
    camera = new THREE.PerspectiveCamera(50, 1, 0.1, 3000);
    if (THREE.OrbitControls) { controls = new THREE.OrbitControls(camera, renderer.domElement); controls.enableDamping = true; controls.minDistance = 6; controls.maxDistance = 220; }
    hemi = new THREE.HemisphereLight(0xbfd8ff, 0x1a2238, 0.6); scene.add(hemi);
    sunLight = new THREE.DirectionalLight(0xfff2d0, 1.2); scene.add(sunLight);
    sunMesh = new THREE.Mesh(new THREE.SphereGeometry(9, 32, 16), new THREE.MeshBasicMaterial({ color: 0xffe08a, fog: false }));
    sunGlow = new THREE.Mesh(new THREE.SphereGeometry(16, 32, 16), new THREE.MeshBasicMaterial({ color: 0xffc24d, transparent: true, opacity: 0.25, fog: false }));
    scene.add(sunMesh); scene.add(sunGlow);
    const sg = new THREE.BufferGeometry(), sp = [];
    for (let i = 0; i < 1500; i++) { const r = 900, a = Math.random() * Math.PI * 2, b = Math.random() * Math.PI * 0.48; sp.push(r * Math.cos(a) * Math.cos(b), r * Math.sin(b), r * Math.sin(a) * Math.cos(b)); }
    sg.setAttribute('position', new THREE.Float32BufferAttribute(sp, 3));
    stars = new THREE.Points(sg, new THREE.PointsMaterial({ color: 0xcfe0ff, size: 1.6, sizeAttenuation: false, transparent: true, fog: false })); scene.add(stars);
    ground = new THREE.Group();
    const gm = new THREE.Mesh(new THREE.CircleGeometry(700, 64), new THREE.MeshStandardMaterial({ color: 0x1d3b2a, roughness: 1 })); gm.rotation.x = -Math.PI / 2; ground.add(gm);
    const grid = new THREE.GridHelper(1400, 140, 0x2f5a44, 0x234434); grid.position.y = 0.05; ground.add(grid);
    for (let k = 0; k < 60; k++) { const h = 2 + Math.random() * 10; const hill = new THREE.Mesh(new THREE.ConeGeometry(8 + Math.random() * 16, h, 6), new THREE.MeshStandardMaterial({ color: 0x24493a, flatShading: true })); const a = Math.random() * Math.PI * 2, r = 60 + Math.random() * 500; hill.position.set(Math.cos(a) * r, h / 2, Math.sin(a) * r); ground.add(hill); }
    scene.add(ground);
    clock = new THREE.Clock();
    resize(); window.addEventListener('resize', resize);
    (function loop() { requestAnimationFrame(loop); tick(clock.getDelta()); })();
    ready = true;
    return true;
  }
  function resize() { if (!renderer) return; const w = host.clientWidth || 800, h = host.clientHeight || 520; renderer.setSize(w, h); camera.aspect = w / h; camera.updateProjectionMatrix(); }

  function cellTexture() {
    const c = document.createElement('canvas'); c.width = 512; c.height = 64; const g = c.getContext('2d');
    g.fillStyle = '#0a1f4d'; g.fillRect(0, 0, 512, 64);
    for (let x = 0; x < 512; x += 16) for (let y = 0; y < 64; y += 16) { g.fillStyle = '#16367f'; g.fillRect(x + 1, y + 1, 14, 14); g.strokeStyle = '#4c7de8'; g.lineWidth = 0.6; g.beginPath(); g.moveTo(x + 8, y + 1); g.lineTo(x + 8, y + 15); g.stroke(); }
    const t = new THREE.CanvasTexture(c); t.wrapS = t.wrapT = THREE.RepeatWrapping; return t;
  }

  function build(geo) {
    if (plane) scene.remove(plane);
    props = []; flows = [];
    plane = new THREE.Group();
    const span = Math.min(30, Math.max(10, 8 + geo.span_m * 0.9)), chord = span / Math.max(6, geo.aspect_ratio);
    const white = new THREE.MeshStandardMaterial({ color: 0xe9eef8, roughness: 0.5, metalness: 0.1 });
    const wing = new THREE.Group();
    const wb = new THREE.Mesh(new THREE.BoxGeometry(chord, chord * 0.1, span), white); wing.add(wb);
    if (geo.panel_fraction > 0) {
      const tex = cellTexture(); tex.repeat.set(1, Math.max(1, span / chord / 4));
      const pnl = new THREE.Mesh(new THREE.PlaneGeometry(chord * 0.88, span * Math.min(0.97, geo.panel_fraction / 0.82)), new THREE.MeshStandardMaterial({ map: tex, metalness: 0.6, roughness: 0.25, emissive: 0x0a1a40, emissiveIntensity: 0.4 }));
      pnl.rotation.x = -Math.PI / 2; pnl.position.y = chord * 0.051; wing.add(pnl);
    }
    [-1, 1].forEach(s => { const tip = new THREE.Mesh(new THREE.BoxGeometry(chord * 0.9, chord * 0.12, span * 0.12), white); tip.position.set(-chord * 0.02, chord * 0.05 + span * 0.012, s * span * 0.53); tip.rotation.x = s * 0.18; wing.add(tip); });
    plane.add(wing);
    const fus = new THREE.Mesh(new THREE.CylinderGeometry(chord * 0.16, chord * 0.1, chord * 2.2, 18), white); fus.rotation.z = Math.PI / 2; fus.position.set(chord * 0.3, -chord * 0.12, 0); plane.add(fus);
    const boom = new THREE.Mesh(new THREE.CylinderGeometry(chord * 0.05, chord * 0.04, span * 0.38, 10), white); boom.rotation.z = Math.PI / 2; boom.position.set(-span * 0.19, -chord * 0.05, 0); plane.add(boom);
    const ht = new THREE.Mesh(new THREE.BoxGeometry(chord * 0.6, chord * 0.05, span * 0.22), white); ht.position.set(-span * 0.37, 0, 0); plane.add(ht);
    const vt = new THREE.Mesh(new THREE.BoxGeometry(chord * 0.6, span * 0.08, chord * 0.05), white); vt.position.set(-span * 0.37, span * 0.04, 0); plane.add(vt);
    batMesh = new THREE.Mesh(new THREE.BoxGeometry(chord * 0.5, chord * 0.18, chord * 0.18), new THREE.MeshStandardMaterial({ color: 0x5cff9d, emissive: 0x5cff9d, emissiveIntensity: 0.4, transparent: true, opacity: 0.95 })); batMesh.position.set(chord * 0.4, -chord * 0.12, 0); plane.add(batMesh);
    const nm = Math.max(1, geo.n_motors || 1);
    const mpos = nm === 1 ? [new THREE.Vector3(chord * 1.42, -chord * 0.12, 0)] : Array.from({ length: nm }, (_, i) => new THREE.Vector3(chord * 0.75, 0, (i - (nm - 1) / 2) * span * 0.5 / Math.max(1, nm - 1)));
    mpos.forEach(p => {
      const pod = new THREE.Mesh(new THREE.CylinderGeometry(chord * 0.07, chord * 0.05, chord * 0.5, 12), new THREE.MeshStandardMaterial({ color: 0xff7a45, emissive: 0xff7a45, emissiveIntensity: 0.35 })); pod.rotation.z = Math.PI / 2; pod.position.copy(p).add(new THREE.Vector3(-chord * 0.2, 0, 0)); plane.add(pod);
      const hub = new THREE.Group(); hub.position.copy(p).add(new THREE.Vector3(chord * 0.08, 0, 0));
      for (let b = 0; b < 2; b++) { const bl = new THREE.Mesh(new THREE.BoxGeometry(chord * 0.03, chord * 0.9, chord * 0.07), new THREE.MeshStandardMaterial({ color: 0x2a2f3c })); bl.rotation.x = b * Math.PI; bl.position.y = b ? -chord * 0.45 : chord * 0.45; hub.add(bl); }
      plane.add(hub); props.push(hub);
    });
    const mk = (pts, color, kind, n) => {
      const curve = new THREE.CatmullRomCurve3(pts);
      const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(n * 3), 3));
      const pnts = new THREE.Points(g, new THREE.PointsMaterial({ color, size: Math.max(0.12, chord * 0.09), transparent: true, depthWrite: false, blending: THREE.AdditiveBlending }));
      plane.add(pnts); flows.push({ curve, pnts, n, kind, phase: Math.random() });
    };
    if (geo.panel_fraction > 0) { [-0.35, -0.15, 0.15, 0.35].forEach(z => mk([new THREE.Vector3(0, chord * 0.06, z * span), new THREE.Vector3(chord * 0.3, chord * 0.05, z * span * 0.4), batMesh.position.clone()], 0x5cff9d, 'charge', 22)); }
    mpos.forEach(p => mk([batMesh.position.clone(), new THREE.Vector3((batMesh.position.x + p.x) / 2, -chord * 0.05, p.z * 0.5), p], 0xc79bff, 'drive', 30));
    plane.scale.setScalar(1);
    scene.add(plane);
    if (rays) scene.remove(rays);
    const rg = new THREE.BufferGeometry(); rg.setAttribute('position', new THREE.BufferAttribute(new Float32Array(120 * 3), 3));
    rays = new THREE.Points(rg, new THREE.PointsMaterial({ color: 0xffb020, size: 0.18, transparent: true, opacity: 0.85, depthWrite: false })); scene.add(rays);
    rays.userData = { seeds: Array.from({ length: 120 }, () => ({ u: Math.random(), z: (Math.random() - 0.5) * span * 0.9, x: (Math.random() - 0.5) * chord })) };
    orbitR = Math.max(26, span * 2.2);
  }

  function load(result) {
    if (!ready) return;
    data = result.series;
    build(result.geometry);
    peakSun = Math.max(1, ...data.p_solar); peakReq = Math.max(1, ...data.p_req);
    simT = 0; idx = 0;
    update();
    const p = plane.position; camera.position.set(p.x - 30, p.y + 14, p.z + 34); if (controls) controls.target.copy(p);
  }

  function sample(t) { const T = data.t_h; let lo = 0, hi = T.length - 1; if (t <= T[0]) return 0; if (t >= T[hi]) return hi; while (hi - lo > 1) { const m = (lo + hi) >> 1; if (T[m] <= t) lo = m; else hi = m; } return lo; }

  function update() {
    if (!data || !plane) return;
    idx = sample(simT / 3600);
    const i = idx, el = data.sun_el[i] * Math.PI / 180, az = data.sun_az[i] * Math.PI / 180;
    const R = 800, sx = -R * Math.cos(el) * Math.cos(az), sz = R * Math.cos(el) * Math.sin(az), sy = R * Math.sin(el);
    sunMesh.position.set(sx, sy, sz); sunGlow.position.copy(sunMesh.position);
    sunMesh.visible = sunGlow.visible = el > -0.05;
    sunLight.position.set(sx, Math.max(sy, 10), sz); sunLight.intensity = Math.max(0, Math.min(1.3, Math.sin(el) * 2.2));
    const day = Math.max(0, Math.min(1, (data.sun_el[i] + 4) / 14)), dusk = Math.max(0, 1 - Math.abs(data.sun_el[i] - 2) / 8);
    const sky = NIGHT.clone().lerp(DAY, day).lerp(DUSK, dusk * 0.55 * (1 - day * 0.5));
    scene.background = sky; scene.fog.color = sky; hemi.intensity = 0.15 + 0.6 * day;
    stars.material.opacity = 1 - day;
    const prev = plane.position.clone();
    const ang = (simT / 3600) * 2 * Math.PI * 1.2;
    plane.position.set(Math.cos(ang) * orbitR, 12 + data.alt[i] * 0.0025 + 0.004 * Math.min(data.alt[i], 2000), Math.sin(ang) * orbitR);
    plane.rotation.set(0, -ang - Math.PI / 2 + Math.PI, 0.22);
    plane.rotateZ(data.mode[i] === 'climb' ? 0.1 : data.mode[i] === 'glide' ? -0.08 : 0);
    const d = plane.position.clone().sub(prev); camera.position.add(d); if (controls) controls.target.add(d);
    if (onFrame) onFrame(i, simT / 3600);
  }

  function tick(dt) {
    if (!renderer) return;
    if (data && playing) { simT += dt * speed; const end = data.t_h[data.t_h.length - 1] * 3600; if (simT >= end) { simT = end; playing = false; if (window.SolScene.onEnd) window.SolScene.onEnd(); } update(); }
    if (data && plane) {
      const i = idx, ps = data.p_solar[i] / peakSun, pr = data.p_prop[i] / Math.max(1, Math.max(...[peakReq])), net = data.p_solar[i] - data.p_req[i];
      props.forEach(h => { h.rotation.x += dt * (1 + 40 * Math.min(1, data.p_prop[i] / peakReq * 1.6)) * (playing ? 1 : 0.2); });
      batMesh.material.emissiveIntensity = 0.15 + 0.7 * Math.max(0, data.soc[i]);
      batMesh.material.color.setHex(data.soc[i] > 0.3 ? 0x5cff9d : data.soc[i] > 0.1 ? 0xffc24d : 0xff5d73);
      flows.forEach(f => {
        const lvl = f.kind === 'charge' ? Math.max(0, Math.min(1, net / peakSun * 2)) : Math.min(1, Math.max(0, (data.p_req[i] - data.p_solar[i]) / peakReq * 1.5) + (data.p_prop[i] > 0 && data.p_solar[i] <= 0 ? 0.3 : 0));
        f.phase = (f.phase + dt * (0.2 + 1.2 * lvl) * (playing ? 1 : 0.3)) % 1;
        const pos = f.pnts.geometry.attributes.position.array, vis = Math.round(f.n * lvl);
        for (let k = 0; k < f.n; k++) { const u = (k / f.n + f.phase) % 1, p = f.curve.getPointAt(u); if (k < vis) { pos[3 * k] = p.x; pos[3 * k + 1] = p.y; pos[3 * k + 2] = p.z; } else { pos[3 * k] = pos[3 * k + 1] = pos[3 * k + 2] = 1e5; } }
        f.pnts.geometry.attributes.position.needsUpdate = true;
      });
      if (rays) {
        const pos = rays.geometry.attributes.position.array, dir = sunMesh.position.clone().normalize();
        const vis = data.p_solar[i] > 0 ? Math.round(120 * Math.min(1, ps * 1.2)) : 0;
        rays.userData.seeds.forEach((s, k) => {
          s.u = (s.u + dt * 0.9 * (playing ? 1 : 0.3)) % 1;
          if (k < vis) { const base = new THREE.Vector3(s.x, 0.3, s.z).applyQuaternion(plane.quaternion).add(plane.position); const p = base.add(dir.clone().multiplyScalar((1 - s.u) * 40)); pos[3 * k] = p.x; pos[3 * k + 1] = p.y; pos[3 * k + 2] = p.z; } else { pos[3 * k] = pos[3 * k + 1] = pos[3 * k + 2] = 1e5; }
        });
        rays.geometry.attributes.position.needsUpdate = true;
      }
    }
    if (controls) controls.update();
    renderer.render(scene, camera);
  }

  window.SolScene = {
    init, load, resize,
    play() { if (!data) return; if (simT >= data.t_h[data.t_h.length - 1] * 3600) simT = 0; playing = true; },
    pause() { playing = false; }, isPlaying() { return playing; },
    setSpeed(s) { speed = s; },
    seek(f) { if (!data) return; simT = f * data.t_h[data.t_h.length - 1] * 3600; update(); },
    progress() { return data ? simT / (data.t_h[data.t_h.length - 1] * 3600) : 0; },
    set onFrame(cb) { onFrame = cb; }, onEnd: null
  };
})();
