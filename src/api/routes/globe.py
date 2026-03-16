"""GET /globe — 3D interactive globe showing Jerome7 builders worldwide."""

from datetime import datetime

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse, JSONResponse

from src.api.meta import head_meta
from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession

from src.db.database import get_db
from src.db.models import User, Streak, Session as SessionModel, Pod, PodMember
from src.agents.session_types import today_session_type

router = APIRouter()

# Lat/lng for top 50 countries (ISO alpha-2)
_COORDS = {
    "US": (37.09, -95.71), "CA": (56.13, -106.35), "MX": (23.63, -102.55),
    "BR": (-14.24, -51.93), "AR": (-38.42, -63.62), "CO": (4.57, -74.30),
    "PE": (-9.19, -75.02), "CL": (-35.68, -71.54), "VE": (6.42, -66.59),
    "GB": (55.38, -3.44), "FR": (46.23, 2.21), "DE": (51.17, 10.45),
    "ES": (40.46, -3.75), "IT": (41.87, 12.57), "NL": (52.13, 5.29),
    "SE": (60.13, 18.64), "NO": (60.47, 8.47), "CH": (46.82, 8.23),
    "PT": (39.40, -8.22), "PL": (51.92, 19.15), "IE": (53.14, -7.69),
    "AT": (47.52, 14.55), "BE": (50.50, 4.47), "DK": (56.26, 9.50),
    "FI": (61.92, 25.75), "CZ": (49.82, 15.47), "RO": (45.94, 24.97),
    "GR": (39.07, 21.82), "HU": (47.16, 19.50),
    "TR": (38.96, 35.24), "RU": (61.52, 105.32), "UA": (48.38, 31.17),
    "JP": (36.20, 138.25), "KR": (35.91, 127.77), "CN": (35.86, 104.20),
    "IN": (20.59, 78.96), "SG": (1.35, 103.82), "ID": (-0.79, 113.92),
    "TH": (15.87, 100.99), "PH": (12.88, 121.77), "MY": (4.21, 101.98),
    "VN": (14.06, 108.28), "PK": (30.38, 69.35), "BD": (23.68, 90.36),
    "AE": (23.42, 53.85), "SA": (23.89, 45.08), "IL": (31.05, 34.85),
    "AU": (-25.27, 133.78), "NZ": (-40.90, 174.89),
    "NG": (9.08, 8.68), "KE": (-0.02, 37.91), "ZA": (-30.56, 22.94),
    "EG": (26.82, 30.80), "GH": (7.95, -1.02), "ET": (9.15, 40.49),
    "MA": (31.79, -7.09), "TZ": (-6.37, 34.89),
}

_COUNTRY_NAMES = {
    "US": "United States", "CA": "Canada", "MX": "Mexico",
    "BR": "Brazil", "AR": "Argentina", "CO": "Colombia",
    "PE": "Peru", "CL": "Chile", "VE": "Venezuela",
    "GB": "United Kingdom", "FR": "France", "DE": "Germany",
    "ES": "Spain", "IT": "Italy", "NL": "Netherlands",
    "SE": "Sweden", "NO": "Norway", "CH": "Switzerland",
    "PT": "Portugal", "PL": "Poland", "IE": "Ireland",
    "AT": "Austria", "BE": "Belgium", "DK": "Denmark",
    "FI": "Finland", "CZ": "Czech Republic", "RO": "Romania",
    "GR": "Greece", "HU": "Hungary",
    "TR": "Turkey", "RU": "Russia", "UA": "Ukraine",
    "JP": "Japan", "KR": "South Korea", "CN": "China",
    "IN": "India", "SG": "Singapore", "ID": "Indonesia",
    "TH": "Thailand", "PH": "Philippines", "MY": "Malaysia",
    "VN": "Vietnam", "PK": "Pakistan", "BD": "Bangladesh",
    "AE": "UAE", "SA": "Saudi Arabia", "IL": "Israel",
    "AU": "Australia", "NZ": "New Zealand",
    "NG": "Nigeria", "KE": "Kenya", "ZA": "South Africa",
    "EG": "Egypt", "GH": "Ghana", "ET": "Ethiopia",
    "MA": "Morocco", "TZ": "Tanzania",
}


@router.get("/globe/data")
def globe_data(db: DBSession = Depends(get_db)):
    now = datetime.utcnow()
    today_start = datetime(now.year, now.month, now.day)

    # Country user counts
    country_rows = (
        db.query(User.country, func.count(User.id))
        .filter(User.country.isnot(None))
        .group_by(User.country)
        .all()
    )

    # Sessions today per country
    sessions_today_rows = (
        db.query(User.country, func.count(SessionModel.id))
        .join(User, SessionModel.user_id == User.id)
        .filter(SessionModel.logged_at >= today_start, User.country.isnot(None))
        .group_by(User.country)
        .all()
    )
    sessions_today_map = dict(sessions_today_rows)

    countries = []
    for code, count in country_rows:
        if code in _COORDS:
            lat, lng = _COORDS[code]
            countries.append({
                "code": code,
                "name": _COUNTRY_NAMES.get(code, code),
                "lat": lat,
                "lng": lng,
                "users": count,
                "sessions_today": sessions_today_map.get(code, 0),
            })

    # Pod connections — users in the same pod from different countries
    connections = []
    try:
        pods = db.query(Pod).all()
    except Exception:
        pods = []
    for pod in pods:
        members = (
            db.query(PodMember, User)
            .join(User, PodMember.user_id == User.id)
            .filter(PodMember.pod_id == pod.id, PodMember.status == "active")
            .all()
        )
        member_countries = set()
        for pm, user in members:
            if user.country and user.country in _COORDS:
                member_countries.add(user.country)
        country_list = sorted(member_countries)
        for i in range(len(country_list)):
            for j in range(i + 1, len(country_list)):
                connections.append({
                    "from": country_list[i],
                    "to": country_list[j],
                    "type": "pod",
                })

    # Dedupe connections
    seen = set()
    unique_connections = []
    for c in connections:
        key = (c["from"], c["to"])
        if key not in seen:
            seen.add(key)
            unique_connections.append(c)

    # Stats
    total_builders = db.query(User).count()
    num_countries = len(countries)
    sessions_today = db.query(SessionModel).filter(
        SessionModel.logged_at >= today_start
    ).count()
    top_streak = db.query(Streak).order_by(Streak.current_streak.desc()).first()
    longest_streak = top_streak.current_streak if top_streak else 0

    return JSONResponse({
        "countries": countries,
        "connections": unique_connections,
        "stats": {
            "total_builders": total_builders,
            "total_jeromes": total_builders,
            "countries": num_countries,
            "sessions_today": sessions_today,
            "longest_streak": longest_streak,
            "session_type": today_session_type(),
        },
    })


@router.get("/globe", response_class=HTMLResponse)
def globe_page():
    _meta = head_meta(
        title="Jerome7 — The Global Graph",
        description="Jerome7 builders worldwide. Every dot is someone who showed up.",
        url="https://jerome7.com/globe",
    )
    html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Jerome7 — The Global Graph</title>
<meta name="description" content="Jerome7 builders worldwide. Every dot is someone who showed up.">
""" + _meta + """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700;800&display=swap" rel="stylesheet">
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: #0a0a0a; color: #c9d1d9;
    font-family: 'JetBrains Mono', monospace;
    overflow: hidden; height: 100vh; width: 100vw;
  }

  /* Nav */
  .nav {
    position: fixed; top: 0; left: 0; right: 0; z-index: 100;
    display: flex; justify-content: space-between; align-items: center;
    padding: 16px 24px;
  }
  .brand { font-size: 11px; letter-spacing: 3px; color: #E85D04; text-decoration: none; font-weight: 700; }
  .nav-links { display: flex; gap: 20px; }
  .nav-links a { font-size: 11px; color: #484f58; text-decoration: none; letter-spacing: 1px; }
  .nav-links a:hover { color: #E85D04; }

  /* Title overlay */
  .title-overlay {
    position: fixed; bottom: 40px; left: 40px; z-index: 100;
    pointer-events: none;
  }
  .title-main {
    font-size: 28px; font-weight: 800; color: #f0f6fc;
    letter-spacing: 6px; line-height: 1;
  }
  .title-sub {
    font-size: 12px; color: #484f58; margin-top: 8px;
    letter-spacing: 1px;
  }

  /* Stats panel — glass morphism */
  .stats-panel {
    position: fixed; top: 70px; right: 24px; z-index: 100;
    background: rgba(13, 17, 23, 0.75);
    backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 12px; padding: 20px 24px;
    min-width: 200px;
  }
  .stat-row {
    display: flex; justify-content: space-between; align-items: baseline;
    padding: 8px 0; border-bottom: 1px solid rgba(255, 255, 255, 0.04);
  }
  .stat-row:last-child { border-bottom: none; }
  .stat-label { font-size: 9px; letter-spacing: 2px; color: #484f58; }
  .stat-val { font-size: 18px; font-weight: 800; color: #f0f6fc; }
  .stat-val.orange { color: #e8713a; }
  .stat-val.green { color: #3fb950; }

  /* Tooltip */
  .tooltip {
    position: fixed; z-index: 200; pointer-events: none;
    background: rgba(13, 17, 23, 0.9);
    backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
    border: 1px solid rgba(232, 113, 58, 0.3);
    border-radius: 8px; padding: 10px 14px;
    font-size: 11px; color: #f0f6fc;
    display: none; white-space: nowrap;
  }
  .tooltip-country { font-weight: 700; color: #e8713a; }
  .tooltip-stat { color: #8b949e; margin-top: 2px; }

  /* Canvas */
  #globe-canvas { display: block; width: 100vw; height: 100vh; }

  /* Mobile flat map fallback */
  .flat-map {
    display: none; position: fixed; inset: 0; z-index: 50;
    overflow-y: auto; padding: 80px 20px 120px;
  }
  .flat-map-title {
    font-size: 10px; letter-spacing: 3px; color: #e8713a;
    margin-bottom: 16px;
  }
  .flat-map-grid {
    display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
    gap: 8px;
  }
  .flat-map-item {
    background: rgba(22, 27, 34, 0.8); border: 1px solid #21262d;
    border-radius: 8px; padding: 12px; text-align: center;
  }
  .flat-map-item .dot {
    width: 10px; height: 10px; border-radius: 50%;
    background: #e8713a; margin: 0 auto 8px; display: block;
  }
  .flat-map-item .name { font-size: 11px; color: #f0f6fc; font-weight: 600; }
  .flat-map-item .count { font-size: 10px; color: #484f58; margin-top: 2px; }

  @media (max-width: 768px) {
    #globe-canvas { display: none; }
    .flat-map { display: block; }
    .title-overlay { bottom: 20px; left: 20px; }
    .title-main { font-size: 18px; letter-spacing: 3px; }
    .stats-panel { top: auto; bottom: 80px; right: 12px; left: 12px; min-width: auto; }
  }
</style>
</head>
<body>

<nav class="nav">
  <a href="/" class="brand">JEROME7</a>
  <div class="nav-links">
    <a href="/timer">SESSION</a>
    <a href="https://discord.gg/5AZP8DbEJm">DISCORD</a>
    <a href="https://github.com/odominguez7/Jerome7">GITHUB</a>
  </div>
</nav>

<div class="stats-panel" id="stats-panel">
  <div class="stat-row">
    <span class="stat-label">BUILDERS</span>
    <span class="stat-val orange" id="stat-builders">--</span>
  </div>
  <div class="stat-row">
    <span class="stat-label">COUNTRIES</span>
    <span class="stat-val" id="stat-countries">--</span>
  </div>
  <div class="stat-row">
    <span class="stat-label">TODAY</span>
    <span class="stat-val green" id="stat-today">--</span>
  </div>
  <div class="stat-row">
    <span class="stat-label">LONGEST CHAIN</span>
    <span class="stat-val" id="stat-streak">--</span>
  </div>
</div>

<div class="title-overlay">
  <div class="title-main">THE GLOBAL GRAPH</div>
  <div class="title-sub">Every dot is a builder who showed up today.</div>
</div>

<div class="tooltip" id="tooltip">
  <div class="tooltip-country" id="tooltip-country"></div>
  <div class="tooltip-stat" id="tooltip-stat"></div>
</div>

<canvas id="globe-canvas"></canvas>

<div class="flat-map" id="flat-map">
  <div class="flat-map-title">BUILDERS WORLDWIDE</div>
  <div class="flat-map-grid" id="flat-map-grid"></div>
</div>

<script src="https://cdn.jsdelivr.net/npm/three@0.162.0/build/three.min.js"></script>
<script>
(function() {
  // --- Data ---
  let globeData = { countries: [], connections: [], stats: {} };

  async function fetchData() {
    try {
      const r = await fetch('/globe/data');
      globeData = await r.json();
      updateStats();
      updateFlatMap();
      if (window.innerWidth > 768) buildPins();
    } catch(e) { console.error('Globe data fetch failed:', e); }
  }

  function updateStats() {
    const s = globeData.stats;
    document.getElementById('stat-builders').textContent = s.total_builders || 0;
    document.getElementById('stat-countries').textContent = s.countries || 0;
    document.getElementById('stat-today').textContent = s.sessions_today || 0;
    document.getElementById('stat-streak').textContent = s.longest_streak || 0;
  }

  function updateFlatMap() {
    const grid = document.getElementById('flat-map-grid');
    grid.innerHTML = '';
    const sorted = [...globeData.countries].sort((a, b) => b.users - a.users);
    if (sorted.length === 0) {
      grid.innerHTML = '<div style="color:#484f58;font-size:12px;grid-column:1/-1;text-align:center;padding:40px">Waiting for the first builder...</div>';
      return;
    }
    for (const c of sorted) {
      const el = document.createElement('div');
      el.className = 'flat-map-item';
      const size = Math.max(8, Math.min(24, 8 + c.users * 2));
      el.innerHTML = `<span class="dot" style="width:${size}px;height:${size}px"></span>
        <div class="name">${c.name}</div>
        <div class="count">${c.users} builder${c.users !== 1 ? 's' : ''}</div>`;
      grid.appendChild(el);
    }
  }

  // --- Three.js globe (desktop only) ---
  if (window.innerWidth <= 768) { fetchData(); return; }

  const canvas = document.getElementById('globe-canvas');
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 0.1, 1000);
  camera.position.z = 3.2;

  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
  renderer.setSize(window.innerWidth, window.innerHeight);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setClearColor(0x0a0a0a, 1);

  // --- Globe sphere with canvas texture ---
  const texSize = 2048;
  const texCanvas = document.createElement('canvas');
  texCanvas.width = texSize;
  texCanvas.height = texSize;
  const ctx = texCanvas.getContext('2d');

  // Dark ocean
  ctx.fillStyle = '#0d1117';
  ctx.fillRect(0, 0, texSize, texSize);

  // Draw a simplified continent outline using lat/lng grid
  // We'll use a grid pattern for a tech/data aesthetic
  ctx.strokeStyle = 'rgba(33, 38, 45, 0.6)';
  ctx.lineWidth = 1;
  // Latitude lines
  for (let lat = -80; lat <= 80; lat += 20) {
    const y = (1 - (lat + 90) / 180) * texSize;
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(texSize, y);
    ctx.stroke();
  }
  // Longitude lines
  for (let lng = -180; lng <= 180; lng += 30) {
    const x = ((lng + 180) / 360) * texSize;
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, texSize);
    ctx.stroke();
  }

  // Continent approximations — filled polygons in subtle blue
  ctx.fillStyle = 'rgba(30, 50, 80, 0.35)';
  function drawRegion(points) {
    ctx.beginPath();
    for (let i = 0; i < points.length; i++) {
      const x = ((points[i][1] + 180) / 360) * texSize;
      const y = (1 - (points[i][0] + 90) / 180) * texSize;
      if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    }
    ctx.closePath();
    ctx.fill();
  }

  // Rough continent blobs
  // North America
  drawRegion([[70,-170],[70,-55],[50,-55],[25,-80],[15,-90],[15,-105],[30,-120],[50,-130],[60,-170]]);
  // South America
  drawRegion([[15,-80],[15,-35],[-5,-35],[-20,-40],[-55,-70],[-55,-75],[-15,-80],[0,-80]]);
  // Europe
  drawRegion([[72,-10],[72,40],[45,40],[35,30],[35,-10],[45,-10]]);
  // Africa
  drawRegion([[37,-10],[37,40],[10,45],[-35,30],[-35,15],[5,-10]]);
  // Asia
  drawRegion([[72,40],[72,180],[10,140],[10,100],[25,55],[35,30],[45,40]]);
  // Australia
  drawRegion([[-10,115],[-10,155],[-40,150],[-40,115]]);

  const texture = new THREE.CanvasTexture(texCanvas);

  const globeGeo = new THREE.SphereGeometry(1, 64, 64);
  const globeMat = new THREE.MeshPhongMaterial({
    map: texture,
    transparent: false,
    shininess: 5,
  });
  const globe = new THREE.Mesh(globeGeo, globeMat);
  scene.add(globe);

  // Wireframe overlay
  const wireGeo = new THREE.SphereGeometry(1.002, 48, 48);
  const wireMat = new THREE.MeshBasicMaterial({
    color: 0x1a2332,
    wireframe: true,
    transparent: true,
    opacity: 0.15,
  });
  const wireframe = new THREE.Mesh(wireGeo, wireMat);
  scene.add(wireframe);

  // Atmosphere glow
  const glowGeo = new THREE.SphereGeometry(1.06, 64, 64);
  const glowMat = new THREE.ShaderMaterial({
    vertexShader: `
      varying vec3 vNormal;
      void main() {
        vNormal = normalize(normalMatrix * normal);
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }
    `,
    fragmentShader: `
      varying vec3 vNormal;
      void main() {
        float intensity = pow(0.65 - dot(vNormal, vec3(0.0, 0.0, 1.0)), 3.0);
        gl_FragColor = vec4(0.15, 0.35, 0.65, 1.0) * intensity;
      }
    `,
    blending: THREE.AdditiveBlending,
    side: THREE.BackSide,
    transparent: true,
  });
  const glow = new THREE.Mesh(glowGeo, glowMat);
  scene.add(glow);

  // Lighting
  const ambient = new THREE.AmbientLight(0x334455, 1.2);
  scene.add(ambient);
  const dirLight = new THREE.DirectionalLight(0xffffff, 0.6);
  dirLight.position.set(5, 3, 5);
  scene.add(dirLight);

  // Stars
  const starGeo = new THREE.BufferGeometry();
  const starVerts = [];
  for (let i = 0; i < 3000; i++) {
    starVerts.push(
      (Math.random() - 0.5) * 100,
      (Math.random() - 0.5) * 100,
      (Math.random() - 0.5) * 100
    );
  }
  starGeo.setAttribute('position', new THREE.Float32BufferAttribute(starVerts, 3));
  const starMat = new THREE.PointsMaterial({ color: 0x444444, size: 0.05 });
  scene.add(new THREE.Points(starGeo, starMat));

  // --- Pins and arcs ---
  const pinGroup = new THREE.Group();
  scene.add(pinGroup);
  const arcGroup = new THREE.Group();
  scene.add(arcGroup);

  // Pin mesh data for raycasting
  const pinMeshes = [];

  function latLngToVec3(lat, lng, radius) {
    const phi = (90 - lat) * Math.PI / 180;
    const theta = (lng + 180) * Math.PI / 180;
    return new THREE.Vector3(
      -radius * Math.sin(phi) * Math.cos(theta),
      radius * Math.cos(phi),
      radius * Math.sin(phi) * Math.sin(theta)
    );
  }

  function buildPins() {
    // Clear previous
    while (pinGroup.children.length) pinGroup.remove(pinGroup.children[0]);
    while (arcGroup.children.length) arcGroup.remove(arcGroup.children[0]);
    pinMeshes.length = 0;

    const maxUsers = Math.max(1, ...globeData.countries.map(c => c.users));

    for (const country of globeData.countries) {
      const pos = latLngToVec3(country.lat, country.lng, 1.01);
      const scale = 0.01 + (country.users / maxUsers) * 0.04;

      // Glowing dot
      const geo = new THREE.SphereGeometry(scale, 12, 12);
      const mat = new THREE.MeshBasicMaterial({ color: 0xe8713a });
      const mesh = new THREE.Mesh(geo, mat);
      mesh.position.copy(pos);
      mesh.userData = country;
      pinGroup.add(mesh);
      pinMeshes.push(mesh);

      // Outer glow ring
      const ringGeo = new THREE.SphereGeometry(scale * 2.2, 12, 12);
      const ringMat = new THREE.MeshBasicMaterial({
        color: 0xe8713a, transparent: true, opacity: 0.15,
      });
      const ring = new THREE.Mesh(ringGeo, ringMat);
      ring.position.copy(pos);
      pinGroup.add(ring);

      // Pulse animation data
      ring.userData._pulse = true;
      ring.userData._phase = Math.random() * Math.PI * 2;
    }

    // Arcs between pod countries
    const coordMap = {};
    for (const c of globeData.countries) coordMap[c.code] = c;

    for (const conn of globeData.connections) {
      const from = coordMap[conn.from];
      const to = coordMap[conn.to];
      if (!from || !to) continue;

      const start = latLngToVec3(from.lat, from.lng, 1.01);
      const end = latLngToVec3(to.lat, to.lng, 1.01);

      // Bezier arc via midpoint lifted above surface
      const mid = new THREE.Vector3().addVectors(start, end).multiplyScalar(0.5);
      const dist = start.distanceTo(end);
      mid.normalize().multiplyScalar(1.0 + dist * 0.3);

      const curve = new THREE.QuadraticBezierCurve3(start, mid, end);
      const points = curve.getPoints(40);
      const arcGeo = new THREE.BufferGeometry().setFromPoints(points);
      const arcMat = new THREE.LineBasicMaterial({
        color: 0xe8713a, transparent: true, opacity: 0.35,
      });
      arcGroup.add(new THREE.Line(arcGeo, arcMat));
    }
  }

  // --- Interaction ---
  let isDragging = false;
  let prevMouse = { x: 0, y: 0 };
  let rotVelX = 0, rotVelY = 0.002; // auto-rotate Y
  let targetRotX = 0, targetRotY = 0;
  const raycaster = new THREE.Raycaster();
  const mouse = new THREE.Vector2();
  const tooltip = document.getElementById('tooltip');
  const tooltipCountry = document.getElementById('tooltip-country');
  const tooltipStat = document.getElementById('tooltip-stat');

  canvas.addEventListener('mousedown', (e) => {
    isDragging = true;
    prevMouse = { x: e.clientX, y: e.clientY };
  });
  canvas.addEventListener('mousemove', (e) => {
    if (isDragging) {
      const dx = e.clientX - prevMouse.x;
      const dy = e.clientY - prevMouse.y;
      targetRotY += dx * 0.005;
      targetRotX += dy * 0.005;
      targetRotX = Math.max(-Math.PI / 2, Math.min(Math.PI / 2, targetRotX));
      prevMouse = { x: e.clientX, y: e.clientY };
    }

    // Tooltip raycasting
    mouse.x = (e.clientX / window.innerWidth) * 2 - 1;
    mouse.y = -(e.clientY / window.innerHeight) * 2 + 1;
    raycaster.setFromCamera(mouse, camera);
    const hits = raycaster.intersectObjects(pinMeshes);
    if (hits.length > 0) {
      const data = hits[0].object.userData;
      tooltipCountry.textContent = data.name;
      tooltipStat.textContent = data.users + ' builder' + (data.users !== 1 ? 's' : '') +
        (data.sessions_today > 0 ? ' \u00b7 ' + data.sessions_today + ' today' : '');
      tooltip.style.display = 'block';
      tooltip.style.left = (e.clientX + 16) + 'px';
      tooltip.style.top = (e.clientY - 10) + 'px';
      canvas.style.cursor = 'pointer';
    } else {
      tooltip.style.display = 'none';
      canvas.style.cursor = isDragging ? 'grabbing' : 'grab';
    }
  });
  canvas.addEventListener('mouseup', () => { isDragging = false; });
  canvas.addEventListener('mouseleave', () => {
    isDragging = false;
    tooltip.style.display = 'none';
  });

  // Touch support
  canvas.addEventListener('touchstart', (e) => {
    if (e.touches.length === 1) {
      isDragging = true;
      prevMouse = { x: e.touches[0].clientX, y: e.touches[0].clientY };
    }
  });
  canvas.addEventListener('touchmove', (e) => {
    if (isDragging && e.touches.length === 1) {
      const dx = e.touches[0].clientX - prevMouse.x;
      const dy = e.touches[0].clientY - prevMouse.y;
      targetRotY += dx * 0.005;
      targetRotX += dy * 0.005;
      targetRotX = Math.max(-Math.PI / 2, Math.min(Math.PI / 2, targetRotX));
      prevMouse = { x: e.touches[0].clientX, y: e.touches[0].clientY };
    }
  });
  canvas.addEventListener('touchend', () => { isDragging = false; });

  // --- Animate ---
  let autoRotAngle = 0;
  let currentRotX = 0, currentRotY = 0;

  function animate() {
    requestAnimationFrame(animate);

    // Auto-rotate when not dragging
    if (!isDragging) {
      autoRotAngle += 0.002;
      targetRotY += 0.001;
    }

    // Smooth interpolation
    currentRotX += (targetRotX - currentRotX) * 0.05;
    currentRotY += (targetRotY - currentRotY) * 0.05;

    globe.rotation.x = currentRotX;
    globe.rotation.y = currentRotY;
    wireframe.rotation.x = currentRotX;
    wireframe.rotation.y = currentRotY;
    pinGroup.rotation.x = currentRotX;
    pinGroup.rotation.y = currentRotY;
    arcGroup.rotation.x = currentRotX;
    arcGroup.rotation.y = currentRotY;

    // Pulse glow rings
    const t = Date.now() * 0.001;
    for (const child of pinGroup.children) {
      if (child.userData._pulse) {
        const s = 1.0 + Math.sin(t * 2 + child.userData._phase) * 0.3;
        child.scale.setScalar(s);
        child.material.opacity = 0.08 + Math.sin(t * 2 + child.userData._phase) * 0.07;
      }
    }

    renderer.render(scene, camera);
  }

  window.addEventListener('resize', () => {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
  });

  fetchData();
  animate();

  // Refresh data every 60s
  setInterval(fetchData, 60000);
})();
</script>
</body>
</html>"""
    return HTMLResponse(content=html)
