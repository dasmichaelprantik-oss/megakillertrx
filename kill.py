"""
Search and Kill - Streamlit edition
=========================================
100 weapons (60 guns, 25 bombs, 15 smokes/gases), 100 battlefields, bots, dogs,
missiles, turrets, jets, teams, character classes and online relay - the COMPLETE
original pygame game, playable inside a Streamlit page.

How it works
  * The original game runs unchanged in a background process (headless pygame).
  * Its frames are streamed to the page as MJPEG; your keyboard/mouse are sent back.

Install:  pip install streamlit pygame
Run:      python mini_militia_streamlit.py   (auto-launches Streamlit)
     or:  streamlit run mini_militia_streamlit.py
          (open the page, press "Click here to play")

Controls:
  A / D or Left / Right  - move
  W / Up / Space (hold)  - jetpack
  Mouse                  - aim            Left click (hold) - shoot
  R reload | Q or wheel  - swap gun       E cycle throwable | G throw
  TAB  arsenal (left click = primary, right click = secondary, bomb/smoke = +5)
  N random loadout | I immortality 2 min | Z immortal tank | H hunting dog | M missile strike
  U machine-gun turret | J 3 fighter jets | K high-speed MG (infinite ammo)
  T teams | C character class | F1 feature panel | F2 battlefield browser
  Esc  close menu

Local use: the game server listens on a local port, so run Streamlit on your own
computer (or LAN) - it is not meant for https cloud hosting.
"""
import os
import sys

IS_GAME = "--game" in sys.argv

# ======================================================================
#                       STREAMLIT FRONT-END (page)
# ======================================================================
if not IS_GAME:
    import atexit
    import socket
    import subprocess
    import tempfile
    import time

    try:
        import streamlit as st
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        import streamlit.components.v1 as components
    except ImportError:
        print("Streamlit is not installed:  pip install streamlit pygame")
        sys.exit(1)

    try:
        _ctx = get_script_run_ctx(suppress_warning=True)
    except TypeError:
        _ctx = get_script_run_ctx()
    if _ctx is None:
        # Started with plain "python file.py" / the VS Code Run button:
        # launch Streamlit automatically instead of just printing a hint.
        import subprocess as _sp
        print("Launching Streamlit... (your browser will open)")
        try:
            sys.exit(_sp.call([sys.executable, "-m", "streamlit", "run", os.path.abspath(__file__)]))
        except KeyboardInterrupt:
            sys.exit(0)

    SCRIPT = os.path.abspath(__file__)

    class _GameManager:
        """Owns the background game process (one per Streamlit server)."""

        def __init__(self):
            self.proc = None
            self.port = None
            self.log_path = None
            atexit.register(self.stop)

        def alive(self):
            return self.proc is not None and self.proc.poll() is None

        def stop(self):
            if self.proc is not None and self.proc.poll() is None:
                self.proc.terminate()
                try:
                    self.proc.wait(timeout=4)
                except Exception:
                    self.proc.kill()
            self.proc = None

        def _tail(self):
            try:
                with open(self.log_path, "r", errors="replace") as fh:
                    return "".join(fh.readlines()[-25:])
            except OSError:
                return ""

        def start(self, mode, net_host, net_port, lan):
            self.stop()
            s = socket.socket()
            s.bind(("127.0.0.1", 0))
            self.port = s.getsockname()[1]
            s.close()
            log = tempfile.NamedTemporaryFile(delete=False, suffix=".log", prefix="militia_")
            self.log_path = log.name
            cmd = [sys.executable, SCRIPT, "--game", "--http-port", str(self.port),
                   "--bind", "0.0.0.0" if lan else "127.0.0.1", "--mode", mode,
                   "--net-host", net_host or "127.0.0.1", "--net-port", str(int(net_port))]
            self.proc = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT)
            deadline = time.time() + 25
            while time.time() < deadline:
                if self.proc.poll() is not None:
                    return False, self._tail()
                try:
                    socket.create_connection(("127.0.0.1", self.port), timeout=0.5).close()
                    return True, ""
                except OSError:
                    time.sleep(0.25)
            return False, "Game did not start in time.\n" + self._tail()

    @st.cache_resource
    def get_manager():
        return _GameManager()

    PLAYER_HTML = r"""
<style>
  html,body{margin:0;background:#0b1220;font-family:Arial,sans-serif;color:#cfe3ff}
  #wrap{position:relative;width:100%;max-width:1000px;margin:0 auto;background:#0b1220}
  #g{width:100%;aspect-ratio:1000/600;display:block;background:#101a2c;user-select:none;
     -webkit-user-drag:none;outline:none}
  #ov{position:absolute;left:0;right:0;top:0;aspect-ratio:1000/600;display:flex;align-items:center;
      justify-content:center;background:rgba(5,10,20,.6);font-weight:700;font-size:22px;
      cursor:pointer;text-align:center;color:#ffe27a}
  #bar{display:flex;justify-content:space-between;align-items:center;font-size:12px;padding:5px 2px}
  button{background:#2b4a70;color:#fff;border:0;border-radius:6px;padding:4px 10px;cursor:pointer}
  #wrap:fullscreen{max-width:none;display:flex;flex-direction:column;justify-content:center}
  #wrap:fullscreen #g{width:auto;height:calc(100vh - 32px);max-width:100vw;margin:0 auto}
  #wrap:fullscreen #ov{height:calc(100vh - 32px);aspect-ratio:auto}
  #touchpad{display:none;position:absolute;inset:auto 0 42px 0;pointer-events:none;justify-content:space-between;align-items:end;padding:10px;z-index:5}
  .touchgroup{display:flex;gap:8px;align-items:end;pointer-events:auto}
  .touchbtn{min-width:54px;min-height:54px;border-radius:50%;background:rgba(25,48,72,.78);border:2px solid rgba(190,220,245,.8);color:white;font-size:13px;font-weight:bold;touch-action:none;user-select:none}
  .touchbtn.fire{min-width:72px;min-height:72px;background:rgba(130,45,35,.8)}
  @media (pointer:coarse), (max-width:700px){#touchpad{display:flex} #ov{font-size:18px} #bar{font-size:10px}}
</style>
<div id="wrap">
  <img id="g" draggable="false" alt="game">
  <div id="ov">&#9654; Tap here to play<br>(touch controls or keyboard + mouse)</div>
  <div id="touchpad">
    <div class="touchgroup">
      <button class="touchbtn" data-key="KeyA">◀</button>
      <button class="touchbtn" data-key="KeyD">▶</button>
      <button class="touchbtn" data-key="Space">JET</button>
    </div>
    <div class="touchgroup">
      <button class="touchbtn" data-key="KeyR">RELOAD</button>
      <button class="touchbtn" data-key="KeyQ">GUN</button>
      <button class="touchbtn fire" id="touchfire">FIRE</button>
    </div>
  </div>
  <div id="bar"><span id="st">connecting...</span><button id="fs">&#x26F6; Fullscreen</button></div>
</div>
<script>
const PORT = __PORT__;
let host = "127.0.0.1";
try { host = window.parent.location.hostname || host; } catch (e) {}
const base = "http://" + host + ":" + PORT;
const img = document.getElementById("g"), ov = document.getElementById("ov"),
      st = document.getElementById("st"), wrap = document.getElementById("wrap");
function connect() { img.src = base + "/stream?t=" + Date.now(); }
img.onload = () => { st.textContent = "connected - click the game to play"; };
img.onerror = () => { st.textContent = "stream lost - retrying..."; setTimeout(connect, 1000); };
connect();

let active = false, buf = [], inflight = false;
// Browser-side procedural weapon audio (works even though the game renderer is headless).
let audioCtx = null, soundCursor = 0, lastSoundKey = "", lastSoundAt = 0;
function ensureAudio() {
  if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  if (audioCtx.state === "suspended") audioCtx.resume().catch(()=>{});
}
function playWeaponSound(rawName) {
  if (!active) return;
  ensureAudio();
  const ctx = audioCtx, now = ctx.currentTime;
  const name = String(rawName || "rifle").toLowerCase();
  // Tiny per-weapon pitch differences keep individual weapons recognizable while
  // preserving a consistent sound family (pistol, shotgun, rifle, launcher, etc.).
  const nameHash = Array.from(name).reduce((n, ch) => (n * 31 + ch.charCodeAt(0)) >>> 0, 7);
  const key = /rocket|missile|rpg|launcher|bazooka|bgm/.test(name) ? "rocket" :
              /shotgun|scatter|double barrel/.test(name) ? "shotgun" :
              /sniper|marksman|railgun/.test(name) ? "sniper" :
              /pistol|revolver|handgun|desert eagle/.test(name) ? "pistol" :
              /minigun|machine gun|gatling|turret/.test(name) ? "mg" :
              /laser|plasma|energy|sci.fi/.test(name) ? "energy" :
              /grenade|bomb|mine|explosive|cluster/.test(name) ? "boom" : "rifle";
  // Avoid stacking a dozen identical synthetic transients during automatic fire.
  if (key === lastSoundKey && now - lastSoundAt < (key === "mg" ? 0.065 : 0.018)) return;
  lastSoundKey = key; lastSoundAt = now;
  let kind = "rifle", duration = 0.12, base = 105;
  if (/rocket|missile|rpg|launcher|bazooka|bgm/.test(name)) { kind="rocket"; duration=0.42; base=55; }
  else if (/shotgun|scatter|double barrel/.test(name)) { kind="shotgun"; duration=0.24; base=78; }
  else if (/sniper|marksman|railgun/.test(name)) { kind="sniper"; duration=0.30; base=65; }
  else if (/pistol|revolver|handgun|desert eagle/.test(name)) { kind="pistol"; duration=0.10; base=145; }
  else if (/minigun|machine gun|gatling|turret/.test(name)) { kind="mg"; duration=0.075; base=120; }
  else if (/laser|plasma|energy|sci.fi/.test(name)) { kind="energy"; duration=0.18; base=520; }
  else if (/grenade|bomb|mine|explosive|cluster/.test(name)) { kind="boom"; duration=0.38; base=48; }
  base *= 0.78 + (nameHash % 45) / 100;
  duration *= 0.92 + ((nameHash >>> 5) % 17) / 100;
  // Noise transient gives the shot a punch; oscillator tail makes weapon families distinct.
  const len = Math.max(1, Math.floor(ctx.sampleRate * duration));
  const buffer = ctx.createBuffer(1, len, ctx.sampleRate), data = buffer.getChannelData(0);
  for (let i=0; i<len; i++) {
    const t=i/len, decay=Math.pow(1-t, kind==="rocket"||kind==="boom"?1.25:4.2);
    data[i]=(Math.random()*2-1)*decay*(kind==="sniper"?0.9:0.65);
  }
  const noise=ctx.createBufferSource(); noise.buffer=buffer;
  const filter=ctx.createBiquadFilter(); filter.type="lowpass";
  filter.frequency.setValueAtTime(kind==="energy"?2200:(kind==="sniper"?1500:900),now);
  if (kind==="rocket"||kind==="boom") filter.frequency.exponentialRampToValueAtTime(120,now+duration);
  const gain=ctx.createGain(); gain.gain.setValueAtTime(kind==="rocket"||kind==="boom"?0.42:0.22,now);
  gain.gain.exponentialRampToValueAtTime(0.001,now+duration);
  noise.connect(filter); filter.connect(gain); gain.connect(ctx.destination); noise.start(now); noise.stop(now+duration);
  const osc=ctx.createOscillator(), og=ctx.createGain();
  osc.type=(kind==="energy"?"sine":(kind==="mg"?"sawtooth":"triangle"));
  osc.frequency.setValueAtTime(base*(kind==="rocket"||kind==="boom"?2.2:1.5),now);
  osc.frequency.exponentialRampToValueAtTime(Math.max(28,base*0.45),now+duration);
  og.gain.setValueAtTime(kind==="energy"?0.10:0.16,now);
  og.gain.exponentialRampToValueAtTime(0.001,now+duration*0.85);
  osc.connect(og); og.connect(ctx.destination); osc.start(now); osc.stop(now+duration);
}
async function pollSounds() {
  if (!active) return;
  try {
    const r=await fetch(base+"/sounds?after="+soundCursor,{cache:"no-store"});
    if (r.ok) { const j=await r.json(); for (const ev of (j.events||[])) { soundCursor=Math.max(soundCursor,ev.id||0); playWeaponSound(ev.name); } }
  } catch(e) {}
  setTimeout(pollSounds, 90);
}
async function flush() {
  if (inflight || !buf.length) return;
  inflight = true;
  const body = JSON.stringify(buf); buf = [];
  try {
    const r = await fetch(base + "/input", {method: "POST", body: body,
                          headers: {"Content-Type": "text/plain"}});
    const j = await r.json();
    img.style.cursor = j.cv ? "default" : "none";
  } catch (e) {}
  inflight = false;
  if (buf.length) flush();
}
function push(ev) {
  if (ev.t === "mm" && buf.length && buf[buf.length - 1].t === "mm") buf[buf.length - 1] = ev;
  else buf.push(ev);
  flush();
}
function pos(e) {
  const r = img.getBoundingClientRect();
  return [Math.max(0, Math.min(999, Math.round((e.clientX - r.left) * 1000 / r.width))),
          Math.max(0, Math.min(599, Math.round((e.clientY - r.top) * 600 / r.height)))];
}
function setActive(v) {
  active = v;
  ov.style.display = v ? "none" : "flex";
  if (v) { ensureAudio(); pollSounds(); }
  if (!v) push({t: "reset"});
}
ov.addEventListener("click", () => { window.focus(); setActive(true); });
window.addEventListener("blur", () => { if (active) setActive(false); });

// Touchscreen controls share the same input channel as keyboard/mouse controls.
document.querySelectorAll("[data-key]").forEach(btn => {
  const code = btn.dataset.key;
  const down = e => { e.preventDefault(); if (!active) return; try{btn.setPointerCapture(e.pointerId)}catch(_){} push({t:"kd",c:code}); };
  const up = e => { e.preventDefault(); push({t:"ku",c:code}); };
  btn.addEventListener("pointerdown", down);
  ["pointerup","pointercancel","lostpointercapture"].forEach(ev => btn.addEventListener(ev, up));
});
const fireBtn = document.getElementById("touchfire");
function fireDown(e){e.preventDefault(); if(!active)return; const r=img.getBoundingClientRect(); const x=r.left+r.width*.78, y=r.top+r.height*.5; push({t:"mm",x:Math.round((x-r.left)*1000/r.width),y:Math.round((y-r.top)*600/r.height)});push({t:"md",x:780,y:300,b:1});}
function fireUp(e){e.preventDefault();push({t:"mu",x:780,y:300,b:1});}
fireBtn.addEventListener("pointerdown",fireDown); ["pointerup","pointercancel","lostpointercapture"].forEach(ev=>fireBtn.addEventListener(ev,fireUp));
// Dragging directly on the game image aims with touch.
img.addEventListener("pointermove", e => {if(!active || e.pointerType==="mouse")return; const p=pos(e);push({t:"mm",x:p[0],y:p[1]});});
img.addEventListener("pointerdown", e => {if(!active || e.pointerType==="mouse")return; const p=pos(e);push({t:"mm",x:p[0],y:p[1]});});
const PASS = new Set(["F5", "F11", "F12"]);
document.addEventListener("keydown", e => {
  if (!active || e.ctrlKey || e.metaKey || e.altKey || PASS.has(e.code)) return;
  e.preventDefault();
  if (e.repeat) return;
  push({t: "kd", c: e.code});
});
document.addEventListener("keyup", e => {
  if (!active || PASS.has(e.code)) return;
  e.preventDefault();
  push({t: "ku", c: e.code});
});
document.addEventListener("mousemove", e => {
  if (!active) return; const p = pos(e); push({t: "mm", x: p[0], y: p[1]});
});
img.addEventListener("mousedown", e => {
  if (!active) return; e.preventDefault();
  const p = pos(e); push({t: "md", x: p[0], y: p[1], b: e.button + 1});
});
document.addEventListener("mouseup", e => {
  if (!active) return; const p = pos(e); push({t: "mu", x: p[0], y: p[1], b: e.button + 1});
});
img.addEventListener("contextmenu", e => e.preventDefault());
img.addEventListener("wheel", e => {
  if (!active) return; e.preventDefault(); push({t: "wh", d: e.deltaY < 0 ? 1 : -1});
}, {passive: false});
document.getElementById("fs").addEventListener("click", () => {
  try { wrap.requestFullscreen(); } catch (e) {}
});
</script>
"""

    st.set_page_config(page_title="Search and Kill", page_icon="🎮", layout="wide")
    st.title("🎮 Search and Kill")

    with st.sidebar:
        st.header("Game setup")
        with st.expander("📱 Device & control settings", expanded=False):
            st.markdown("**Laptop / desktop:** use keyboard and mouse. **Mobile:** open the game in a browser and use the on-screen buttons; drag on the battlefield to aim.")
            st.caption("For a phone on the same Wi-Fi, start Streamlit on the computer with network access enabled and enable the LAN option below. This prototype's game stream is local/LAN-based; it is not directly playable through a public Streamlit cloud URL.")
            mobile_hint = st.selectbox("Control layout", ["Auto (recommended)", "Touchscreen", "Keyboard + mouse"])
            st.caption("Auto layout shows touch controls on touch devices and small screens.")

        mode_label = st.radio("Mode", ["Offline practice", "Host online battle",
                                       "Join a friend's battle"])
        mode = {"Offline practice": "offline", "Host online battle": "host",
                "Join a friend's battle": "join"}[mode_label]
        net_port = st.number_input("Online port", 1024, 65535, 50555, disabled=(mode == "offline"))
        net_host = st.text_input("Friend's IP / hostname", "", disabled=(mode != "join"))
        lan = st.checkbox("Allow other devices on my network to open the game stream", False)
        c1, c2 = st.columns(2)
        start_clicked = c1.button("▶ Start / Restart", type="primary", use_container_width=True)
        stop_clicked = c2.button("■ Stop", use_container_width=True)
        with st.expander("Controls", expanded=False):
            st.markdown(
                "- **A/D**, arrows: move  \n- **W/Up/Space**: jetpack  \n- **Mouse**: aim, **click**: shoot  \n"
                "- **R** reload, **Q**/wheel swap gun  \n- **E** cycle throwable, **G** throw  \n"
                "- **TAB** arsenal (all 100 items)  \n- **N** random loadout, **I** immortality  \n"
                "- **Z** immortal tank (match-long): left-click infinite MG, right-click infinite rockets  \n- **H** dog, **M** missile, **U** turret, **J** jets, **K** infinite MG  \n"
                "- **T** teams, **C** classes, **F1** features, **F2** 100 battlefields  \n"
                "- **Esc** close menu  \n- Distinct browser-generated audio for pistols, rifles, shotguns, sniper weapons, machine guns, rockets and explosions")

    mgr = get_manager()
    if stop_clicked:
        mgr.stop()
        st.session_state["stopped"] = True
    if start_clicked:
        st.session_state["stopped"] = False
        mgr.stop()
    if not mgr.alive() and not st.session_state.get("stopped"):
        with st.spinner("Starting the battlefield..."):
            ok, err = mgr.start(mode, net_host, net_port, lan)
        if not ok:
            st.error("The game could not start. Is pygame installed (`pip install pygame`, or `pip install pygame-ce` on Python 3.13+)?")
            st.code(err or "(no output)")
            st.session_state["stopped"] = True

    if mgr.alive():
        components.html(PLAYER_HTML.replace("__PORT__", str(mgr.port)), height=670, scrolling=False)
        st.caption("Click the game once to capture keyboard and mouse. Click outside it to release.")
    else:
        st.info("Game stopped. Press **Start / Restart** in the sidebar.")
    st.stop()

# ======================================================================
#                       GAME PROCESS (headless pygame)
# ======================================================================
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import math
import random
import sys
import socket
import threading
import json
import time
import uuid

import pygame

pygame.init()
W, H = 1000, 600
WORLD_W, WORLD_H = 4200, 1000
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("Search and Kill - 100 Weapons & 100 Battlefields")
clock = pygame.time.Clock()
font = pygame.font.SysFont("arial", 20, bold=True)
small = pygame.font.SysFont("arial", 15, bold=True)
tiny = pygame.font.SysFont("arial", 12, bold=True)
big_font = pygame.font.SysFont("arial", 44, bold=True)
fx_layer = pygame.Surface((W, H), pygame.SRCALPHA)
flash_surf = pygame.Surface((W, H))
flash_surf.fill((255, 255, 255))

GRAVITY = 1400
RUN_SPEED = 260
JET_THRUST = 2600
MAX_RISE = 420
MAX_FALL = 800
NUM_BOTS = 4
RESPAWN = 3.0

platforms = [
    pygame.Rect(0, 950, WORLD_W, 50),       # ground
    pygame.Rect(-40, 0, 40, WORLD_H),       # left wall
    pygame.Rect(WORLD_W, 0, 40, WORLD_H),   # right wall
    pygame.Rect(0, -40, WORLD_W, 40),       # ceiling
    pygame.Rect(200, 800, 300, 25),
    pygame.Rect(650, 700, 260, 25),
    pygame.Rect(1050, 800, 300, 25),
    pygame.Rect(1450, 700, 300, 25),
    pygame.Rect(400, 560, 280, 25),
    pygame.Rect(900, 480, 240, 25),
    pygame.Rect(1300, 540, 280, 25),
    pygame.Rect(150, 400, 240, 25),
    pygame.Rect(1650, 400, 250, 25),
    pygame.Rect(700, 300, 200, 25),
    pygame.Rect(1100, 280, 200, 25),
    pygame.Rect(0, 820, 40, 130),
    pygame.Rect(960, 850, 80, 100),
]

SPAWNS = [(250, 700), (700, 600), (1100, 700), (1500, 600),
          (450, 460), (950, 380), (1700, 300), (200, 300), (1150, 180)]


# =====================================================================
# 100 SELECTABLE BATTLEFIELDS (procedurally generated, each with a theme
# and a distinct platform layout). Press F2 to open the battlefield browser.
# =====================================================================
MAP_THEMES = [
    ("Jungle Strike", (104, 160, 105), (50, 100, 65)),
    ("Desert Outpost", (218, 177, 105), (155, 105, 54)),
    ("Arctic Base", (190, 220, 235), (100, 155, 190)),
    ("Volcanic Zone", (100, 65, 65), (180, 75, 40)),
    ("Neon City", (55, 65, 115), (70, 220, 210)),
    ("Moon Station", (105, 110, 125), (165, 170, 190)),
    ("Forest Ruins", (95, 135, 90), (120, 95, 65)),
    ("Coastal Fortress", (95, 170, 205), (215, 195, 130)),
    ("Industrial Yard", (105, 110, 115), (190, 145, 70)),
    ("Sky Arena", (125, 175, 230), (210, 220, 245)),
]
MAPS = []
for _mi in range(100):
    _theme_name, _sky, _ground = MAP_THEMES[_mi % len(MAP_THEMES)]
    MAPS.append({
        "name": f"{_theme_name} {_mi // len(MAP_THEMES) + 1:02d}",
        "sky": _sky, "ground": _ground, "seed": 4100 + _mi,
        "layout": _mi % 10
    })
selected_map = 0
map_page = 0
map_menu = False


WORLD_DECOR = []


def apply_battlefield(index):
    """Build a wide, scrolling military sandbox with multiple combat districts."""
    global platforms, SPAWNS, selected_map, WORLD_DECOR
    selected_map = index % len(MAPS)
    spec = MAPS[selected_map]
    rng = random.Random(spec["seed"])
    ground_y = 950
    new_platforms = [
        pygame.Rect(0, ground_y, WORLD_W, WORLD_H - ground_y),
        pygame.Rect(-40, 0, 40, WORLD_H),
        pygame.Rect(WORLD_W, 0, 40, WORLD_H),
        pygame.Rect(0, -40, WORLD_W, 40),
    ]
    decor = []
    # Four broad districts create a battlefield you can explore instead of a small arena.
    district_types = ["base", "urban", "industrial", "wilds", "port", "desert", "arctic", "ruins"]
    district = district_types[index % len(district_types)]
    spacing = WORLD_W / 7
    for lane in range(1, 7):
        cx = int(lane * spacing + rng.randint(-100, 100))
        style = (spec["layout"] + lane) % 6
        if style == 0:  # rooftop route
            for j in range(3):
                x = cx - 160 + j * 125
                y = 700 - j * 100
                new_platforms.append(pygame.Rect(x, y, rng.randint(95, 145), 24))
            decor.append(("building", cx - 150, 710, 120, 240))
            decor.append(("building", cx + 5, 610, 120, 340))
        elif style == 1:  # fortified checkpoint
            new_platforms.extend([
                pygame.Rect(cx - 145, 815, 95, 28), pygame.Rect(cx + 45, 815, 95, 28),
                pygame.Rect(cx - 25, 690, 50, 125), pygame.Rect(cx - 120, 560, 105, 20),
                pygame.Rect(cx + 25, 520, 105, 20)])
            decor.append(("watchtower", cx - 32, 620, 64, 330))
        elif style == 2:  # warehouse / container stacks
            new_platforms.extend([
                pygame.Rect(cx - 180, 840, 115, 30), pygame.Rect(cx - 55, 790, 115, 30),
                pygame.Rect(cx + 70, 840, 115, 30), pygame.Rect(cx - 60, 670, 120, 22)])
            decor.extend([("container", cx - 180, 790, 115, 60),
                          ("container", cx - 55, 740, 115, 50),
                          ("container", cx + 70, 790, 115, 60)])
        elif style == 3:  # natural ravine and ridge
            for j in range(4):
                new_platforms.append(pygame.Rect(cx - 200 + j * 105, 780 - (j % 2) * 115,
                                                 rng.randint(80, 115), 20))
            decor.extend([("tree", cx - 175, 800, 60, 120), ("tree", cx + 110, 795, 65, 125)])
        elif style == 4:  # bridge and elevated sniper route
            new_platforms.extend([pygame.Rect(cx - 200, 700, 150, 22),
                                  pygame.Rect(cx - 50, 660, 100, 22),
                                  pygame.Rect(cx + 50, 700, 150, 22),
                                  pygame.Rect(cx - 20, 830, 40, 120)])
            decor.append(("bridge", cx - 205, 690, 410, 24))
        else:  # low cover with a broken tower
            for j in range(4):
                new_platforms.append(pygame.Rect(cx - 180 + j * 105, 860, 75, 30))
            new_platforms.append(pygame.Rect(cx - 35, 610, 70, 22))
            decor.append(("ruin", cx - 55, 650, 110, 300))
    # Extra small traversable platforms keep routes connected across the huge map.
    for x in range(140, WORLD_W - 180, 220):
        if rng.random() < 0.82:
            y = rng.choice([740, 790, 830, 860])
            new_platforms.append(pygame.Rect(x + rng.randint(-45, 45), y,
                                             rng.randint(95, 165), rng.choice([18, 22, 26])))
    # Decorative landmarks in the background; their positions are deterministic per map.
    for x in range(80, WORLD_W - 80, 125):
        if rng.random() < 0.52:
            kind = rng.choice(["tree", "barricade", "antenna", "crater", "sandbag"])
            decor.append((kind, x + rng.randint(-30, 30), rng.choice([825, 850, 875]),
                          rng.randint(35, 90), rng.randint(35, 125)))
    platforms = new_platforms
    WORLD_DECOR = decor
    # Spawn points cover the full map; bots and the player are spread across districts.
    SPAWNS = [(180, 760), (700, 760), (1250, 760), (1850, 760),
              (2450, 760), (3050, 760), (3700, 760), (900, 520),
              (2750, 560), (3950, 700)]
    for idx, fighter in enumerate(everyone):
        sx, sy = SPAWNS[idx % len(SPAWNS)]
        fighter.spawn()
        fighter.x = max(20, min(WORLD_W - fighter.W - 20, sx))
        fighter.y = sy


def draw_map_selection():
    screen.fill((13, 20, 32))
    pygame.draw.rect(screen, (25, 38, 58), (18, 18, W-36, H-36), border_radius=16)
    title = big_font.render("SELECT BATTLEFIELD", True, (120, 225, 255))
    screen.blit(title, (W//2-title.get_width()//2, 28))
    spec = MAPS[selected_map]
    info = small.render(f"Current: {selected_map+1:03d}/100  |  {spec['name']}  |  F2 or ESC to return",
                        True, (240, 240, 245))
    screen.blit(info, (35, 88))
    start = map_page * 25
    for slot, idx in enumerate(range(start, min(start+25, len(MAPS)))):
        col, row = slot % 5, slot // 5
        x, y = 32 + col*188, 125 + row*82
        rect = pygame.Rect(x, y, 176, 70)
        spec = MAPS[idx]
        pygame.draw.rect(screen, spec["sky"], rect, border_radius=8)
        # Tiny platform preview gives each choice a recognisable silhouette.
        rng = random.Random(spec["seed"])
        for j in range(4):
            px = x + 12 + j*39
            py = y + 43 - rng.randint(0, 25)
            pygame.draw.rect(screen, spec["ground"], (px, py, 29, 5), border_radius=2)
        border = (255, 235, 90) if idx == selected_map else (215, 225, 240)
        pygame.draw.rect(screen, border, rect, 3 if idx == selected_map else 1, border_radius=8)
        label = tiny.render(f"{idx+1:03d}. {spec['name']}", True, (15, 20, 28))
        screen.blit(label, (x+7, y+7))
    prev = pygame.Rect(35, 545, 160, 34)
    nxt = pygame.Rect(W-195, 545, 160, 34)
    pygame.draw.rect(screen, (55, 90, 125), prev, border_radius=7)
    pygame.draw.rect(screen, (55, 90, 125), nxt, border_radius=7)
    screen.blit(small.render("< PREVIOUS 25", True, (255,255,255)), (prev.x+15, prev.y+8))
    screen.blit(small.render("NEXT 25 >", True, (255,255,255)), (nxt.x+35, nxt.y+8))
    screen.blit(tiny.render(f"Page {map_page+1}/4  •  Click a card to deploy", True, (200,220,240)), (420, 555))

# =====================================================================
#                          ITEM DEFINITIONS
# =====================================================================
CAT_COLOR = {
    "Pistol": (210, 210, 210), "SMG": (255, 205, 90), "Rifle": (120, 220, 120),
    "Shotgun": (255, 150, 90), "Sniper": (120, 200, 255), "LMG": (200, 160, 255),
    "Launcher": (255, 100, 100), "Energy": (90, 255, 230), "Special": (255, 120, 220),
    "Bomb": (255, 170, 60), "Smoke": (190, 200, 215),
}
GUN_LEN = {"Pistol": 20, "SMG": 24, "Rifle": 30, "Shotgun": 28, "Sniper": 42,
           "LMG": 32, "Launcher": 36, "Energy": 28, "Special": 30}


def gun(name, cat, dmg, delay, mag, reload, speed=950, spread=0.02, pellets=1, **kw):
    d = dict(name=name, cat=cat, type='gun', dmg=dmg, delay=delay, mag=mag, reload=reload,
             speed=speed, spread=spread, pellets=pellets, life=1.2, color=(255, 230, 90),
             size=3, auto=True, burst=1, radius=0, fx=None, fxt=0.0, grav=0, pierce=0,
             bounce=0, homing=0, steal=0, accel=0, recoil=0, style='bullet', zone=None,
             zone_chance=1.0, cluster=0, kb=None)
    d.update(kw)
    return d


def bomb(name, cat, **kw):
    d = dict(name=name, cat=cat, type='bomb', mode='timer', fuse=2.5, radius=0, dmg=0,
             kb=None, bounce=0.45, cluster=0, zone=None, burst_fx=None, teleport=False,
             chain=0, pulse=0, trigger=0, color=(90, 110, 90), size=6)
    d.update(kw)
    return d


def zdef(r, life, color, **kw):
    z = dict(r=r, life=life, color=color, alpha=150, dps=0, fx=None, fxt=0.5, heal=0,
             pull=0, blocks=False, stealth=False, fire=False, end_blast=None)
    z.update(kw)
    return z


def fire_zone(r, life, dps):
    return zdef(r, life, (255, 120, 30), alpha=170, dps=dps, fx='burn', fxt=2.0, fire=True)


def smoke(name, zd=None, **kw):
    kw.setdefault('fuse', 1.3)
    kw.setdefault('size', 5)
    return bomb(name, "Smoke", type='smoke', zone=zd, **kw)


GUNS = [
    # ---------------- Pistols (8)
    gun("Peashooter", "Pistol", 8, 0.22, 12, 1.0, auto=False),
    gun("Revolver", "Pistol", 30, 0.5, 6, 1.7, speed=1100, auto=False, recoil=60),
    gun("Hand Cannon", "Pistol", 42, 0.75, 7, 1.9, speed=1150, size=4, auto=False, recoil=120),
    gun("Auto Pistol", "Pistol", 8, 0.09, 18, 1.2, spread=0.05),
    gun("Dual Pistols", "Pistol", 8, 0.14, 24, 1.5, spread=0.08, pellets=2),
    gun("Silent Pistol", "Pistol", 11, 0.18, 14, 1.1, speed=1300, size=2, auto=False,
        color=(190, 190, 210)),
    gun("Tracker Pistol", "Pistol", 9, 0.3, 10, 1.4, speed=650, homing=2.5, life=1.8,
        color=(120, 255, 255)),
    gun("Flare Pistol", "Pistol", 10, 0.6, 6, 1.6, speed=750, fx='burn', fxt=3, style='ball',
        size=4, grav=200, auto=False, color=(255, 120, 30)),
    # ---------------- SMGs (8)
    gun("Micro SMG", "SMG", 6, 0.05, 30, 1.4, spread=0.09),
    gun("Tactical SMG", "SMG", 8, 0.07, 25, 1.3, spread=0.06),
    gun("Machine Pistol", "SMG", 7, 0.06, 20, 1.2, spread=0.10),
    gun("Bullpup SMG", "SMG", 9, 0.08, 35, 1.6, spread=0.04, speed=1000),
    gun("Hornet SMG", "SMG", 5, 0.04, 45, 1.8, spread=0.12, speed=1050),
    gun("Heavy SMG", "SMG", 11, 0.09, 30, 1.6, spread=0.05),
    gun("Frost SMG", "SMG", 7, 0.08, 30, 1.5, fx='slow', fxt=2.0, color=(140, 210, 255)),
    gun("Venom SMG", "SMG", 6, 0.07, 30, 1.5, fx='poison', fxt=3.0, color=(120, 255, 80)),
    # ---------------- Rifles (10)
    gun("Assault Rifle", "Rifle", 9, 0.11, 20, 1.5),
    gun("Carbine", "Rifle", 8, 0.09, 25, 1.4, spread=0.03),
    gun("Burst Rifle", "Rifle", 10, 0.3, 24, 1.5, spread=0.015, burst=3),
    gun("Heavy AR", "Rifle", 13, 0.14, 24, 1.8, speed=1000),
    gun("Marksman AR", "Rifle", 20, 0.22, 15, 1.7, speed=1250, spread=0.005),
    gun("Rapid AR", "Rifle", 7, 0.07, 30, 1.6, spread=0.05),
    gun("Incendiary AR", "Rifle", 8, 0.12, 22, 1.7, fx='burn', fxt=2.5, color=(255, 140, 40)),
    gun("Bouncer AR", "Rifle", 9, 0.12, 22, 1.6, bounce=3, life=2.0, color=(255, 120, 255)),
    gun("Shock Rifle", "Rifle", 8, 0.13, 22, 1.7, fx='stun', fxt=0.25, color=(120, 160, 255)),
    gun("Vampire Rifle", "Rifle", 9, 0.12, 22, 1.7, steal=0.5, color=(255, 60, 100)),
    # ---------------- Shotguns (8)
    gun("Pump Shotgun", "Shotgun", 7, 0.8, 6, 2.0, speed=900, spread=0.14, pellets=8,
        life=0.55, recoil=140, auto=False),
    gun("Sawed-Off", "Shotgun", 8, 0.5, 2, 1.6, speed=900, spread=0.22, pellets=10,
        life=0.4, recoil=200, auto=False),
    gun("Auto Shotgun", "Shotgun", 5, 0.28, 10, 2.2, speed=900, spread=0.16, pellets=6,
        life=0.5, recoil=100),
    gun("Double Barrel", "Shotgun", 9, 0.45, 2, 1.8, speed=900, spread=0.12, pellets=8,
        life=0.55, recoil=170, auto=False),
    gun("Slug Gun", "Shotgun", 40, 0.9, 5, 2.0, speed=1100, spread=0.01, size=5,
        recoil=150, auto=False),
    gun("Flak Cannon", "Shotgun", 10, 0.9, 5, 2.2, speed=850, spread=0.15, pellets=5,
        life=0.6, radius=45, style='ball', color=(255, 170, 70), auto=False),
    gun("Dragon's Breath", "Shotgun", 4, 0.7, 6, 2.0, speed=800, spread=0.20, pellets=9,
        life=0.45, fx='burn', fxt=3, style='ball', color=(255, 100, 20), auto=False),
    gun("Frost Scatter", "Shotgun", 5, 0.7, 6, 2.0, speed=850, spread=0.18, pellets=8,
        life=0.5, fx='slow', fxt=2.5, color=(160, 220, 255), auto=False),
    # ---------------- Snipers (6)
    gun("Bolt Sniper", "Sniper", 75, 1.3, 5, 2.4, speed=2000, spread=0.0, life=1.5,
        auto=False, recoil=100),
    gun("Semi Sniper", "Sniper", 45, 0.55, 8, 2.2, speed=1800, spread=0.003, life=1.5,
        auto=False),
    gun("Anti-Materiel", "Sniper", 60, 1.4, 4, 2.6, speed=2200, spread=0.0, pierce=3, size=5,
        life=1.5, auto=False, recoil=200),
    gun("Rail Sniper", "Sniper", 55, 1.6, 3, 2.4, speed=3000, spread=0.0, pierce=9,
        style='laser', color=(120, 255, 255), life=1.0, auto=False),
    gun("Explosive Sniper", "Sniper", 40, 1.5, 4, 2.4, speed=1800, spread=0.0, radius=70,
        life=1.5, color=(255, 150, 60), auto=False),
    gun("Silent Sniper", "Sniper", 50, 0.9, 6, 2.0, speed=2000, spread=0.0, steal=0.3,
        life=1.5, auto=False, color=(180, 180, 200)),
    # ---------------- LMGs (4)
    gun("Light MG", "LMG", 9, 0.08, 50, 2.8, spread=0.05),
    gun("Heavy MG", "LMG", 14, 0.10, 60, 3.2, spread=0.06, speed=1000),
    gun("Minigun", "LMG", 6, 0.035, 120, 4.0, spread=0.09, speed=1000),
    gun("Drum Gun", "LMG", 8, 0.07, 75, 3.0, spread=0.05),
    # ---------------- Launchers (6)
    gun("Rocket Launcher", "Launcher", 55, 1.2, 3, 2.2, speed=520, accel=500, radius=110,
        style='rocket', auto=False, recoil=180, life=3.0, kb=700),
    gun("Mini Rocket", "Launcher", 22, 0.4, 8, 2.0, speed=700, accel=400, radius=70,
        style='rocket', life=2.0),
    gun("Homing Missile", "Launcher", 40, 1.3, 3, 2.4, speed=420, accel=250, homing=3.2,
        radius=95, style='rocket', life=3.5, color=(120, 255, 160), auto=False),
    gun("Grenade Launcher", "Launcher", 45, 0.8, 6, 2.2, speed=700, grav=900, bounce=2,
        radius=90, style='ball', life=2.2, auto=False, color=(120, 160, 90)),
    gun("Cluster Launcher", "Launcher", 25, 1.2, 4, 2.4, speed=650, grav=800, radius=60,
        cluster=5, style='ball', life=2.0, auto=False, color=(220, 170, 60)),
    gun("Nuke Launcher", "Launcher", 150, 3.0, 1, 4.0, speed=380, grav=250, radius=260,
        kb=1200, style='ball', size=8, life=4.0, auto=False, color=(255, 60, 60)),
    # ---------------- Energy (5)
    gun("Laser Pistol", "Energy", 12, 0.2, 16, 1.4, speed=1800, style='laser',
        color=(255, 60, 60), spread=0.01),
    gun("Laser Rifle", "Energy", 10, 0.09, 30, 1.8, speed=2000, style='laser', pierce=1,
        color=(80, 255, 120), spread=0.015),
    gun("Plasma Gun", "Energy", 14, 0.16, 20, 1.7, speed=900, style='plasma', radius=35,
        color=(180, 90, 255), size=5),
    gun("Ion Cannon", "Energy", 30, 0.6, 8, 2.2, speed=1000, style='plasma', radius=60,
        fx='stun', fxt=0.8, color=(80, 160, 255), size=7, auto=False),
    gun("Gravity Gun", "Energy", 6, 0.5, 10, 2.0, speed=600, style='plasma',
        zone=zdef(130, 1.8, (150, 90, 255), alpha=70, pull=1500), color=(150, 90, 255),
        size=6, auto=False),
    # ---------------- Special (5)
    gun("Flamethrower", "Special", 1.5, 0.03, 120, 2.5, speed=520, life=0.38, spread=0.12,
        fx='burn', fxt=2.0, style='flame', pierce=99, color=(255, 140, 30)),
    gun("Napalm Thrower", "Special", 1.2, 0.05, 80, 3.0, speed=480, life=0.45, spread=0.14,
        fx='burn', fxt=5.0, style='flame', pierce=99, color=(255, 90, 20),
        zone=fire_zone(70, 4, 12), zone_chance=0.05),
    gun("Freeze Ray", "Special", 1.2, 0.05, 100, 2.5, speed=600, life=0.5, spread=0.05,
        fx='slow', fxt=2.5, style='flame', pierce=99, color=(150, 220, 255)),
    gun("Acid Sprayer", "Special", 1.6, 0.04, 100, 2.5, speed=560, life=0.5, spread=0.08,
        fx='poison', fxt=4.0, style='flame', pierce=99, color=(130, 255, 60)),
    gun("Crossbow", "Special", 48, 0.9, 3, 2.0, speed=1300, grav=300, pierce=1, size=4,
        auto=False, color=(200, 160, 100), life=2.0),
]

BOMBS = [
    bomb("Frag Grenade", "Bomb", fuse=2.2, radius=110, dmg=70),
    bomb("Mini Frag", "Bomb", fuse=1.6, radius=75, dmg=45, size=5),
    bomb("Heavy Frag", "Bomb", fuse=2.8, radius=150, dmg=95, size=8),
    bomb("Impact Grenade", "Bomb", mode='impact', fuse=6, radius=95, dmg=60,
         color=(200, 80, 60)),
    bomb("Sticky Bomb", "Bomb", mode='sticky', fuse=1.8, radius=100, dmg=85,
         color=(80, 200, 80)),
    bomb("Cluster Bomb", "Bomb", fuse=1.8, radius=70, dmg=40, cluster=6,
         color=(200, 160, 60)),
    bomb("Mega Cluster", "Bomb", fuse=2.0, radius=90, dmg=50, cluster=12, size=8,
         color=(220, 120, 40)),
    bomb("Proximity Mine", "Bomb", mode='mine', fuse=999, radius=120, dmg=85, trigger=80,
         color=(160, 60, 60)),
    bomb("Spike Mine", "Bomb", mode='mine', fuse=999, radius=150, dmg=60, kb=1000,
         trigger=100, color=(180, 180, 60)),
    bomb("Molotov", "Bomb", mode='impact', fuse=6, zone=fire_zone(120, 6, 16),
         color=(255, 140, 40)),
    bomb("Napalm Bomb", "Bomb", fuse=2.0, radius=60, dmg=25, zone=fire_zone(190, 9, 14),
         size=8, color=(255, 100, 20)),
    bomb("Thermite", "Bomb", mode='sticky', fuse=1.5, zone=fire_zone(80, 6, 26),
         color=(255, 200, 60)),
    bomb("Freeze Bomb", "Bomb", fuse=1.8, radius=70, dmg=15,
         zone=zdef(150, 6, (150, 220, 255), alpha=120, fx='slow', fxt=2.0),
         color=(150, 220, 255)),
    bomb("Poison Bomb", "Bomb", fuse=1.8, radius=40, dmg=10,
         zone=zdef(150, 8, (110, 230, 60), alpha=130, fx='poison', fxt=3.0),
         color=(110, 220, 60)),
    bomb("EMP Grenade", "Bomb", fuse=1.5,
         burst_fx=dict(r=320, fx='stun', t=2.2, los=False, color=(120, 180, 255)),
         color=(80, 140, 255)),
    bomb("Gravity Bomb", "Bomb", fuse=1.5,
         zone=zdef(120, 3.5, (170, 100, 255), alpha=90, pull=1500), color=(170, 100, 255)),
    bomb("Black Hole", "Bomb", fuse=1.5,
         zone=zdef(110, 3.5, (30, 0, 50), alpha=210, pull=2600, end_blast=(150, 70, 900)),
         size=8, color=(60, 0, 90)),
    bomb("Teleport Bomb", "Bomb", fuse=1.1, teleport=True, color=(80, 255, 255)),
    bomb("Bouncy Bomb", "Bomb", fuse=3.0, bounce=0.97, radius=120, dmg=75,
         color=(255, 90, 200)),
    bomb("Chain Bomb", "Bomb", fuse=2.0, chain=5, radius=70, dmg=40, color=(255, 220, 60)),
    bomb("TNT Brick", "Bomb", fuse=3.5, radius=190, dmg=120, size=9, bounce=0.2,
         color=(200, 40, 40)),
    bomb("Mini Nuke", "Bomb", fuse=4.0, radius=300, dmg=170, kb=1500, size=10, bounce=0.2,
         color=(240, 240, 60)),
    bomb("Shockwave Bomb", "Bomb", fuse=1.5, radius=270, dmg=5, kb=1800,
         color=(255, 255, 255)),
    bomb("Pulse Bomb", "Bomb", fuse=1.6, pulse=4, radius=90, dmg=30, color=(120, 255, 200)),
    bomb("Jump Charge", "Bomb", fuse=0.9, radius=110, dmg=4, kb=1300, color=(255, 160, 0)),
]

SMOKES = [
    smoke("Smoke Grenade", zdef(150, 10, (200, 200, 205), alpha=190, blocks=True),
          color=(200, 200, 205)),
    smoke("Black Smoke", zdef(170, 12, (40, 40, 45), alpha=215, blocks=True),
          color=(50, 50, 55)),
    smoke("Red Smoke", zdef(150, 10, (220, 50, 50), alpha=190, blocks=True),
          color=(220, 50, 50)),
    smoke("Green Smoke", zdef(150, 10, (60, 200, 80), alpha=190, blocks=True),
          color=(60, 200, 80)),
    smoke("Blue Smoke", zdef(150, 10, (60, 110, 230), alpha=190, blocks=True),
          color=(60, 110, 230)),
    smoke("Purple Smoke", zdef(150, 10, (150, 70, 210), alpha=190, blocks=True),
          color=(150, 70, 210)),
    smoke("Thick Fog", zdef(270, 18, (225, 230, 235), alpha=225, blocks=True),
          color=(225, 230, 235), size=7),
    smoke("Flashbang", None, fuse=1.0, color=(255, 255, 255),
          burst_fx=dict(r=450, fx='blind', t=3.5, los=True, color=(255, 255, 255))),
    smoke("Stun Grenade", None, color=(255, 255, 120),
          burst_fx=dict(r=260, fx='stun', t=1.8, los=True, color=(255, 255, 120))),
    smoke("Tear Gas", zdef(160, 10, (230, 230, 150), alpha=140, dps=3, fx='slow', fxt=1.0),
          color=(230, 230, 150)),
    smoke("Toxic Cloud", zdef(160, 10, (110, 200, 40), alpha=150, fx='poison', fxt=2.5),
          color=(110, 200, 40)),
    smoke("Healing Mist", zdef(140, 8, (120, 255, 160), alpha=120, heal=18),
          color=(120, 255, 160)),
    smoke("Haste Mist", zdef(140, 8, (255, 230, 90), alpha=110, fx='haste', fxt=2.0),
          color=(255, 230, 90)),
    smoke("Stealth Cloud", zdef(150, 12, (120, 120, 200), alpha=130, stealth=True, blocks=True),
          color=(120, 120, 200)),
    smoke("Sleep Gas", zdef(140, 7, (170, 120, 230), alpha=140, fx='stun', fxt=0.8),
          color=(170, 120, 230)),
]

ITEMS = GUNS + BOMBS + SMOKES
assert len(GUNS) == 60 and len(BOMBS) == 25 and len(SMOKES) == 15
assert len(ITEMS) == 100 and len({d['name'] for d in ITEMS}) == 100
BY_NAME = {d['name']: d for d in ITEMS}
BOMBLET = bomb("Bomblet", "Bomb", fuse=1.0, radius=60, dmg=30, size=4, bounce=0.5,
               color=(220, 160, 60))


def tags(d):
    t = []
    if d['type'] == 'gun':
        if d['burst'] > 1:
            t.append(f"{d['burst']}-round burst")
        if d['pellets'] > 1:
            t.append(f"{d['pellets']} pellets")
        if not d['auto']:
            t.append("semi-auto")
        if d['radius']:
            t.append("explosive")
        if d['fx']:
            t.append(d['fx'])
        if d['homing']:
            t.append("homing")
        if d['pierce']:
            t.append("pierce")
        if d['bounce']:
            t.append("bouncing")
        if d['steal']:
            t.append("lifesteal")
        if d['cluster']:
            t.append("cluster")
        if d['zone']:
            t.append("field on impact")
        if d['grav']:
            t.append("arcing")
    else:
        t.append({'timer': 'timed fuse', 'impact': 'impact', 'sticky': 'sticky',
                  'mine': 'proximity mine'}[d['mode']])
        if d['radius']:
            t.append(f"blast r{d['radius']}")
        if d['cluster']:
            t.append(f"{d['cluster']} bomblets")
        if d['chain']:
            t.append("chain blasts")
        if d['pulse']:
            t.append("multi-pulse")
        if d['teleport']:
            t.append("teleports you")
        if d['burst_fx']:
            t.append(d['burst_fx']['fx'] + " burst")
        z = d['zone']
        if z:
            if z['fire']:
                t.append("fire")
            if z['blocks']:
                t.append("blocks sight")
            if z['stealth']:
                t.append("stealth")
            if z['heal']:
                t.append("heals")
            if z['pull']:
                t.append("pulls")
            if z['fx']:
                t.append(z['fx'])
            if z['dps']:
                t.append(f"{z['dps']} dps")
    return t


def stat_line(d):
    if d['type'] == 'gun':
        return f"{d['cat']} {d['dmg'] * d['pellets']:g}dmg {60 / d['delay']:.0f}rpm {d['mag']}rd"
    parts = [d['cat']]
    if d['radius']:
        parts.append(f"r{d['radius']}")
    if d['dmg']:
        parts.append(f"{d['dmg']}dmg")
    if d['zone']:
        parts.append(f"zone{d['zone']['r']}/{d['zone']['life']:g}s")
    if d['burst_fx']:
        parts.append("burst")
    return " ".join(parts)


# =====================================================================
#                          GAME STATE
# =====================================================================
S = {'shake': 0.0}
everyone, projectiles, grenades, zones = [], [], [], []
particles, blasts, crates, scheduled, feed = [], [], [], [], []
hunting_dogs, auto_turrets, support_missiles, fighter_jets = [], [], [], []
spg_commandos = []  # Six elite friendly escorts summoned with B
HIGH_SPEED_MG = False  # Player-only rapid-fire mode with unlimited ammunition
TANK_MODE = False  # Immortal tank mode lasts until the match/process ends


def clamp8(v):
    return max(0, min(255, int(v)))


def new_slot(d):
    return {'d': d, 'ammo': d['mag'], 'rt': 0.0}


def feed_add(text):
    feed.append([text, 5.0])
    del feed[:-6]


def schedule(delay, fn):
    scheduled.append([delay, fn])


def add_particle(x, y, vx, vy, life, color, size=3, grav=600):
    if len(particles) < 1200:
        particles.append([x, y, vx, vy, life, life, color, size, grav])


def point_solid(x, y):
    pt = (int(x), int(y))
    for p in platforms:
        if p.collidepoint(pt):
            return True
    return False


def seg_hits_circle(a, b, cx, cy, r):
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    l2 = dx * dx + dy * dy
    t = 0 if l2 == 0 else max(0, min(1, ((cx - ax) * dx + (cy - ay) * dy) / l2))
    px, py = ax + t * dx, ay + t * dy
    return (px - cx) ** 2 + (py - cy) ** 2 < r * r


def line_of_sight(a, b, smoke_block=True):
    ia = (int(a[0]), int(a[1]))
    ib = (int(b[0]), int(b[1]))
    for p in platforms:
        if p.clipline(ia, ib):
            return False
    if smoke_block:
        for z in zones:
            if z.zd['blocks'] and seg_hits_circle(a, b, z.x, z.y, z.r * 0.75):
                return False
    return True


def nearest_enemy(x, y, owner, maxd):
    best, bd = None, maxd * maxd
    for f in everyone:
        if not f.alive or f is owner or f.st['invis'] > 0:
            continue
        cx, cy = f.center
        dd = (cx - x) ** 2 + (cy - y) ** 2
        if dd < bd:
            best, bd = f, dd
    return best


def apply_fx(f, fx, t, owner=None):
    if fx not in f.st:
        return
    f.st[fx] = max(f.st[fx], t)
    if fx in ('burn', 'poison'):
        f.dot_owner = owner


def hurt(f, amt, attacker, name):
    if not f.alive or amt <= 0:
        return
    if attacker is not None and attacker is not f and getattr(attacker, "team", None) == getattr(f, "team", object()):
        return
    # Tank mode grants permanent immunity to the human player, including explosions.
    if getattr(f, 'is_player', False) and TANK_MODE:
        return
    if getattr(f, 'immortal', 0) > 0:
        return  # invulnerable while immortal
    f.hp -= amt
    if f.hp <= 0:
        f.hp = 0
        f.alive = False
        f.deaths += 1
        f.respawn_timer = RESPAWN
        if attacker is not None and attacker is not f:
            attacker.kills += 1
            feed_add(f"{attacker.name} [{name}] > {f.name}")
        else:
            feed_add(f"{f.name} died ({name})")
        cx, cy = f.center
        for _ in range(16):
            add_particle(cx, cy, random.uniform(-220, 220), random.uniform(-300, 60),
                         0.7, (200, 30, 30), 4)
        S['shake'] = max(S['shake'], 6)


def teleport(f, x, y):
    f.x = x - f.W / 2
    f.y = y - f.H / 2 - 4
    f.vx = f.vy = f.kx = 0
    for _ in range(40):
        if any(f.rect.colliderect(p) for p in platforms):
            f.y -= 4
        else:
            break
    f.x = max(0, min(WORLD_W - f.W, f.x))
    f.y = max(0, min(WORLD_H - f.H, f.y))
    for _ in range(14):
        add_particle(x, y, random.uniform(-150, 150), random.uniform(-150, 150),
                     0.5, (80, 255, 255), 3, 0)


def explode(x, y, radius, dmg, owner, name, fx=None, fxt=0.0, kb=None):
    emit_sound(name if name else "Explosion")
    kb = radius * 5 if kb is None else kb
    reach = radius + 18
    for f in everyone:
        if not f.alive:
            continue
        cx, cy = f.center
        dx, dy = cx - x, cy - y
        dist = math.hypot(dx, dy)
        if dist < reach:
            fall = 1 - dist / reach
            amt = dmg * (0.25 + 0.75 * fall)
            if f is owner:
                amt *= 0.6
            nx, ny = (dx / dist, dy / dist) if dist > 1 else (0, -1)
            f.kx = max(-1400, min(1400, f.kx + nx * kb * fall))
            f.vy = max(-1400, min(1400, f.vy + ny * kb * fall * 0.8))
            hurt(f, amt, owner, name)
            if fx:
                apply_fx(f, fx, fxt, owner)
    blasts.append([x, y, radius, 0.35, 0.35, (255, 190, 70)])
    for _ in range(min(45, int(radius / 3) + 4)):
        a = random.uniform(0, math.tau)
        sp = random.uniform(80, 120 + radius * 2)
        add_particle(x, y, math.cos(a) * sp, math.sin(a) * sp, random.uniform(0.3, 0.8),
                     random.choice([(255, 200, 60), (255, 120, 30), (90, 90, 90)]),
                     random.randint(3, 6), 300)
    if everyone and math.hypot(everyone[0].center[0] - x, everyone[0].center[1] - y) < 900:
        S['shake'] = max(S['shake'], min(18, radius / 10))


# ---------------------------------------------------------------- zones
class Zone:
    def __init__(self, x, y, zd, owner, name):
        self.x, self.y = x, y
        self.zd = zd
        self.owner = owner
        self.name = name
        self.life = zd['life']
        self.age = 0.0
        self.puffs = []
        for _ in range(int(zd['r'] / 10) + 10):
            a = random.uniform(0, math.tau)
            rad = math.sqrt(random.random())
            self.puffs.append((math.cos(a) * rad, math.sin(a) * rad,
                               random.uniform(0.25, 0.5), random.uniform(0, 6.28)))

    @property
    def r(self):
        return self.zd['r'] * min(1.0, 0.3 + self.age * 1.2)


def spawn_zone(x, y, zd, owner, name):
    zones.append(Zone(x, y, zd, owner, name))
    if len(zones) > 40:
        zones.pop(0)


def update_zone(z, dt):
    zd = z.zd
    z.age += dt
    z.life -= dt
    r = z.r
    for f in everyone:
        if not f.alive:
            continue
        cx, cy = f.center
        dx, dy = z.x - cx, z.y - cy
        dist = math.hypot(dx, dy)
        if dist < r + 10:
            if zd['dps']:
                hurt(f, zd['dps'] * dt, z.owner, z.name)
            if zd['fx']:
                apply_fx(f, zd['fx'], zd['fxt'], z.owner)
            if zd['heal']:
                f.hp = min(100, f.hp + zd['heal'] * dt)
            if zd['stealth']:
                f.st['invis'] = max(f.st['invis'], 0.3)
        if zd['pull'] and 8 < dist < r * 1.8:
            k = zd['pull'] * dt * (1.2 - dist / (r * 1.8))
            f.kx = max(-1000, min(1000, f.kx + dx / dist * k))
            f.vy += dy / dist * k * 0.8
    if zd['fire'] and random.random() < 0.5:
        a = random.uniform(0, math.tau)
        rr = random.random() * r * 0.8
        add_particle(z.x + math.cos(a) * rr, z.y + math.sin(a) * rr, 0, -80, 0.5,
                     (255, random.randint(100, 200), 40), 3, -100)
    if z.life <= 0:
        eb = zd['end_blast']
        if eb:
            explode(z.x, z.y, eb[0], eb[1], z.owner, z.name, kb=eb[2])


def draw_zone(z, cam):
    zd = z.zd
    fade = max(0.0, min(1.0, z.life / 2.0, z.age / 0.4 + 0.2))
    r = z.r
    base = zd['color']
    for ox, oy, rr, ph in z.puffs:
        px = z.x + ox * r * 0.65 + math.sin(z.age * 1.3 + ph) * r * 0.06 - cam[0]
        py = z.y + oy * r * 0.65 + math.cos(z.age * 1.1 + ph) * r * 0.06 - cam[1]
        if px < -r or px > W + r or py < -r or py > H + r:
            continue
        rad = int(rr * r) + 2
        if zd['fire']:
            py -= abs(math.sin(z.age * 5 + ph)) * r * 0.2
            col = (255, random.randint(80, 180), 30, clamp8(zd['alpha'] * fade))
        else:
            sh = 30 * math.sin(ph + z.age)
            col = (clamp8(base[0] + sh), clamp8(base[1] + sh), clamp8(base[2] + sh),
                   clamp8(zd['alpha'] * fade))
        pygame.draw.circle(fx_layer, col, (int(px), int(py)), rad)
    if zd['pull']:
        pygame.draw.circle(fx_layer, (*base, 90), (int(z.x - cam[0]), int(z.y - cam[1])),
                           int(r * 1.8), 1)


# ------------------------------------------------------------- projectiles
class Projectile:
    def __init__(self, x, y, ang, owner, d):
        self.x, self.y = x, y
        self.vx = math.cos(ang) * d['speed']
        self.vy = math.sin(ang) * d['speed']
        self.owner = owner
        self.d = d
        self.life = d['life']
        self.bounces = d['bounce']
        self.pierce = d['pierce']
        self.hit = set()
        self.dead = False


def kill_projectile(pr):
    if pr.dead:
        return
    pr.dead = True
    d = pr.d
    if d['radius'] > 0:
        explode(pr.x, pr.y, d['radius'], d['dmg'], pr.owner, d['name'], d['fx'], d['fxt'], d['kb'])
    if d['cluster']:
        for _ in range(d['cluster']):
            a = random.uniform(-math.pi, 0)
            sp = random.uniform(150, 450)
            g = Grenade(pr.x, pr.y - 5, math.cos(a) * sp, math.sin(a) * sp, BOMBLET, pr.owner)
            g.fuse = random.uniform(0.5, 1.1)
            grenades.append(g)
    if d['zone'] and random.random() < d['zone_chance']:
        spawn_zone(pr.x, pr.y, d['zone'], pr.owner, d['name'])


def hit_fighter(pr, f):
    d = pr.d
    if d['radius'] > 0:
        kill_projectile(pr)
        return True
    hurt(f, d['dmg'], pr.owner, d['name'])
    if d['fx']:
        apply_fx(f, d['fx'], d['fxt'], pr.owner)
    if d['steal'] and pr.owner.alive:
        pr.owner.hp = min(100, pr.owner.hp + d['dmg'] * d['steal'])
    for _ in range(4):
        add_particle(pr.x, pr.y, random.uniform(-120, 120), random.uniform(-160, 40),
                     0.4, (200, 30, 30), 3)
    pr.hit.add(f)
    if pr.pierce > 0:
        pr.pierce -= 1
        return False
    pr.dead = True
    if d['zone'] and random.random() < d['zone_chance']:
        spawn_zone(pr.x, pr.y, d['zone'], pr.owner, d['name'])
    return True


def update_projectile(pr, dt):
    d = pr.d
    if d['accel']:
        sp = math.hypot(pr.vx, pr.vy)
        if sp > 0:
            k = (sp + d['accel'] * dt) / sp
            pr.vx *= k
            pr.vy *= k
    if d['homing']:
        tgt = nearest_enemy(pr.x, pr.y, pr.owner, 600)
        if tgt:
            tx, ty = tgt.center
            want = math.atan2(ty - pr.y, tx - pr.x)
            cur = math.atan2(pr.vy, pr.vx)
            diff = (want - cur + math.pi) % math.tau - math.pi
            lim = d['homing'] * dt
            cur += max(-lim, min(lim, diff))
            sp = math.hypot(pr.vx, pr.vy)
            pr.vx, pr.vy = math.cos(cur) * sp, math.sin(cur) * sp
    if d['grav']:
        pr.vy += d['grav'] * dt
    if d['style'] == 'rocket' and random.random() < 0.7:
        add_particle(pr.x, pr.y, random.uniform(-40, 40), random.uniform(-40, 40), 0.35,
                     (255, 170, 60), 3, 0)
    dist = math.hypot(pr.vx, pr.vy) * dt
    steps = int(dist // 8) + 1
    sdt = dt / steps
    for _ in range(steps):
        nx = pr.x + pr.vx * sdt
        if point_solid(nx, pr.y):
            if pr.bounces > 0:
                pr.vx = -pr.vx * 0.85
                pr.bounces -= 1
            else:
                kill_projectile(pr)
                return
        else:
            pr.x = nx
        ny = pr.y + pr.vy * sdt
        if point_solid(pr.x, ny):
            if pr.bounces > 0:
                pr.vy = -pr.vy * 0.85
                pr.bounces -= 1
            else:
                kill_projectile(pr)
                return
        else:
            pr.y = ny
        for f in everyone:
            if f.alive and f is not pr.owner and f not in pr.hit and \
                    getattr(f, "team", 0) != getattr(pr.owner, "team", -1) and \
                    f.rect.collidepoint((int(pr.x), int(pr.y))):
                if hit_fighter(pr, f):
                    return
    pr.life -= dt
    if pr.life <= 0:
        kill_projectile(pr)


def draw_projectile(pr, cam):
    d = pr.d
    x, y = int(pr.x - cam[0]), int(pr.y - cam[1])
    if x < -80 or x > W + 80 or y < -80 or y > H + 80:
        return
    col, st = d['color'], d['style']
    if st == 'bullet':
        pygame.draw.line(screen, col, (x, y), (int(x - pr.vx * 0.02), int(y - pr.vy * 0.02)),
                         d['size'])
    elif st == 'laser':
        end = (int(x - pr.vx * 0.025), int(y - pr.vy * 0.025))
        pygame.draw.line(screen, col, (x, y), end, 5)
        pygame.draw.line(screen, (255, 255, 255), (x, y), end, 2)
    elif st == 'ball':
        pygame.draw.circle(screen, col, (x, y), d['size'])
        pygame.draw.circle(screen, (30, 30, 30), (x, y), d['size'], 1)
    elif st == 'plasma':
        pygame.draw.circle(screen, col, (x, y), d['size'] + 2)
        pygame.draw.circle(screen, (255, 255, 255), (x, y), max(1, d['size'] // 2))
    elif st == 'rocket':
        end = (int(x - pr.vx * 0.03), int(y - pr.vy * 0.03))
        pygame.draw.line(screen, (150, 150, 160), (x, y), end, 6)
        pygame.draw.circle(screen, col if d['homing'] else (230, 60, 50), (x, y), 4)
    elif st == 'flame':
        age = 1 - pr.life / d['life']
        rad = int(3 + age * 7)
        c = (clamp8(col[0] - random.randint(0, 40)), clamp8(col[1] - random.randint(0, 40)),
             clamp8(col[2] - random.randint(0, 40)))
        pygame.draw.circle(screen, c, (x, y), rad)


# ---------------------------------------------------------------- grenades
class Grenade:
    def __init__(self, x, y, vx, vy, d, owner):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.d = d
        self.owner = owner
        self.fuse = d['fuse']
        self.stuck = None
        self.off = (0, 0)
        self.age = 0.0
        self.arm = 0.8
        self.dead = False


def detonate(g):
    if g.dead:
        return
    g.dead = True
    d, x, y, o = g.d, g.x, g.y, g.owner
    if d['radius'] > 0:
        explode(x, y, d['radius'], d['dmg'], o, d['name'], kb=d['kb'])
    if d['cluster']:
        for _ in range(d['cluster']):
            a = random.uniform(-math.pi, 0)
            sp = random.uniform(150, 450)
            b = Grenade(x, y - 5, math.cos(a) * sp, math.sin(a) * sp, BOMBLET, o)
            b.fuse = random.uniform(0.5, 1.2)
            grenades.append(b)
    if d['zone']:
        spawn_zone(x, y, d['zone'], o, d['name'])
    bf = d['burst_fx']
    if bf:
        for f in everyone:
            if not f.alive:
                continue
            cx, cy = f.center
            dist = math.hypot(cx - x, cy - y)
            if dist < bf['r'] and (not bf['los'] or line_of_sight((x, y), (cx, cy), False)):
                apply_fx(f, bf['fx'], bf['t'] * (1 - 0.6 * dist / bf['r']), o)
        blasts.append([x, y, bf['r'] * 0.6, 0.3, 0.3, bf['color']])
    if d['teleport'] and o.alive:
        teleport(o, x, y)
    if d['chain']:
        for i in range(d['chain']):
            ox, oy = random.uniform(-150, 150), random.uniform(-90, 40)
            schedule(0.14 * (i + 1), lambda xx=x + ox, yy=y + oy, d=d, o=o:
                     explode(xx, yy, d['radius'], d['dmg'], o, d['name']))
    if d['pulse']:
        for i in range(1, d['pulse']):
            schedule(0.35 * i, lambda xx=x, yy=y, d=d, o=o:
                     explode(xx, yy, d['radius'], d['dmg'], o, d['name']))


def solid_hit(g):
    m = g.d['mode']
    if m == 'impact':
        detonate(g)
        return True
    if m in ('sticky', 'mine'):
        g.stuck = 'wall'
        g.vx = g.vy = 0
        return True
    return False


def update_grenade(g, dt):
    d = g.d
    g.age += dt
    if isinstance(g.stuck, Fighter):
        if not g.stuck.alive:
            g.stuck = None
        else:
            cx, cy = g.stuck.center
            g.x, g.y = cx + g.off[0], cy + g.off[1]
    if g.stuck is None:
        g.vy += 1200 * dt
        sp = math.hypot(g.vx, g.vy)
        n = int(sp * dt // 8) + 1
        sdt = dt / n
        s = d['size']
        for _ in range(n):
            g.x += g.vx * sdt
            hit = False
            r = pygame.Rect(int(g.x - s), int(g.y - s), 2 * s, 2 * s)
            for p in platforms:
                if r.colliderect(p):
                    hit = True
                    if g.vx > 0:
                        g.x = p.left - s
                    elif g.vx < 0:
                        g.x = p.right + s
                    g.vx *= -d['bounce']
                    r = pygame.Rect(int(g.x - s), int(g.y - s), 2 * s, 2 * s)
            g.y += g.vy * sdt
            r = pygame.Rect(int(g.x - s), int(g.y - s), 2 * s, 2 * s)
            for p in platforms:
                if r.colliderect(p):
                    hit = True
                    if g.vy > 0:
                        g.y = p.top - s
                        g.vx *= 0.85
                    elif g.vy < 0:
                        g.y = p.bottom + s
                    g.vy *= -d['bounce']
                    if abs(g.vy) < 60:
                        g.vy = 0
                    r = pygame.Rect(int(g.x - s), int(g.y - s), 2 * s, 2 * s)
            if hit and solid_hit(g):
                break
        if g.dead:
            return
        if g.stuck is None and d['mode'] in ('impact', 'sticky'):
            for f in everyone:
                if f.alive and (f is not g.owner or g.age > 0.35) and \
                        f.rect.collidepoint((int(g.x), int(g.y))):
                    if d['mode'] == 'impact':
                        detonate(g)
                        return
                    g.stuck = f
                    g.off = (g.x - f.center[0], g.y - f.center[1])
                    g.vx = g.vy = 0
                    break
    mode = d['mode']
    if mode in ('timer', 'impact'):
        g.fuse -= dt
    elif mode == 'sticky' and g.stuck is not None:
        g.fuse -= dt
    elif mode == 'mine' and g.stuck is not None:
        g.arm -= dt
        if g.arm <= 0:
            for f in everyone:
                if f.alive and f is not g.owner:
                    cx, cy = f.center
                    if math.hypot(cx - g.x, cy - g.y) < d['trigger']:
                        detonate(g)
                        return
    if mode != 'mine' and g.fuse <= 0:
        detonate(g)


def draw_grenade(g, cam):
    d = g.d
    x, y = int(g.x - cam[0]), int(g.y - cam[1])
    s = d['size']
    if d['mode'] == 'mine':
        pygame.draw.rect(screen, d['color'], (x - s, y - s // 2, 2 * s, s), border_radius=2)
        if g.stuck is not None and g.arm <= 0 and int(g.age * 4) % 2 == 0:
            pygame.draw.circle(screen, (255, 40, 40), (x, y - s // 2), 3)
        return
    blink = g.fuse < 0.7 and int(g.age * 12) % 2 == 0
    pygame.draw.circle(screen, (255, 255, 255) if blink else d['color'], (x, y), s)
    pygame.draw.circle(screen, (20, 20, 20), (x, y), s, 1)


# Military bot classes: each role has a distinctive palette, silhouette and loadout.
BOT_ROLES = {
    "Assault": {"armor": (65, 82, 55), "light": (126, 142, 82), "helmet": (49, 64, 42), "visor": (185, 205, 139), "gun": "Assault Rifle", "detail": "standard"},
    "Sniper": {"armor": (74, 91, 66), "light": (144, 157, 121), "helmet": (47, 61, 45), "visor": (100, 220, 190), "gun": "Sniper Rifle", "detail": "scope"},
    "Heavy Gunner": {"armor": (72, 72, 66), "light": (157, 157, 143), "helmet": (42, 43, 41), "visor": (255, 190, 75), "gun": "LMG", "detail": "heavy"},
    "Special Ops": {"armor": (38, 43, 48), "light": (92, 103, 111), "helmet": (25, 29, 33), "visor": (70, 220, 255), "gun": "SMG", "detail": "night"},
    "Ghost": {"armor": (90, 95, 99), "light": (174, 181, 185), "helmet": (62, 67, 73), "visor": (180, 230, 255), "gun": "Silenced SMG", "detail": "ghost"},
    "Engineer": {"armor": (117, 83, 43), "light": (197, 153, 83), "helmet": (77, 56, 35), "visor": (255, 205, 95), "gun": "Auto Pistol", "detail": "engineer"},
    "Ranger": {"armor": (64, 101, 62), "light": (138, 169, 105), "helmet": (46, 75, 44), "visor": (207, 224, 143), "gun": "Assault Rifle", "detail": "camo"},
    "Tank": {"armor": (80, 78, 66), "light": (173, 162, 124), "helmet": (53, 52, 45), "visor": (255, 167, 65), "gun": "Shotgun", "detail": "shield"},
}
BOT_ROLE_NAMES = list(BOT_ROLES)

# ====================================================================
#                              FIGHTER
# ====================================================================
class Fighter:
    W, H = 24, 42

    def __init__(self, color, is_player=False, name="Bot", role=None):
        self.color = color
        self.is_player = is_player
        self.name = name
        self.team = 1 if is_player else 2
        self.role = role or ("Assault" if is_player else "Assault")
        self.role_data = BOT_ROLES.get(self.role, BOT_ROLES["Assault"])
        self.kills = 0
        self.deaths = 0
        self.respawn_timer = 0
        self.target = None
        self.retarget = 0
        self.wander_t = 0
        self.wander_dir = 0
        primary = self.role_data.get("gun", "Assault Rifle")
        if primary not in BY_NAME:
            primary = "Assault Rifle"
        secondary = "Auto Pistol" if "Auto Pistol" in BY_NAME else primary
        self.slots = [new_slot(BY_NAME[primary]), new_slot(BY_NAME[secondary])]
        self.cur = 0
        self.throwables = []
        self.tsel = 0
        if is_player:
            self.give_throwable(BY_NAME["Frag Grenade"], 3)
            self.give_throwable(BY_NAME["Smoke Grenade"], 2)
        self.spawn()

    # ---------- loadout
    @property
    def slot(self):
        return self.slots[self.cur]

    def random_loadout(self):
        guns = GUNS
        self.slots = [new_slot(random.choice(guns)), new_slot(random.choice(guns))]
        self.cur = 0
        self.throwables = []
        for d in random.sample(BOMBS, 2):
            self.give_throwable(d, 2)
        self.give_throwable(random.choice(SMOKES), 1)
        self.tsel = 0

    def give_throwable(self, d, n):
        for t in self.throwables:
            if t['d'] is d:
                t['n'] += n
                return
        self.throwables.append({'d': d, 'n': n})

    def select_throwable(self, d):
        for i, t in enumerate(self.throwables):
            if t['d'] is d:
                self.tsel = i

    def swap(self):
        self.cur ^= 1
        self.burst_left = 0
        self.cooldown = max(self.cooldown, 0.25)

    def cycle_throwable(self):
        if self.throwables:
            self.tsel = (self.tsel + 1) % len(self.throwables)

    # ---------- lifecycle
    def spawn(self):
        self.x, self.y = random.choice(SPAWNS)
        self.vx = self.vy = self.kx = 0
        self.hp = 100
        self.fuel = 100
        self.cooldown = 0
        self.throw_cd = 2.0
        self.burst_left = 0
        self.burst_t = 0
        self.angle = 0
        self.on_ground = False
        self.blocked = False
        self.anim_phase = getattr(self, "anim_phase", 0.0)
        self.step_timer = random.uniform(0.0, 0.12)
        self.alive = True
        self.face = 1
        self.dot_owner = None
        self.immortal = (10**9 if self.is_player and TANK_MODE else 0.0)  # permanent in tank mode
        self.st = dict(burn=0.0, poison=0.0, slow=0.0, stun=0.0, blind=0.0, haste=0.0,
                       invis=0.0)
        if self.is_player:
            for s in self.slots:
                s['ammo'] = s['d']['mag']
                s['rt'] = 0.0
            if not self.throwables:
                self.give_throwable(BY_NAME["Frag Grenade"], 2)
        else:
            self.random_loadout()

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.W, self.H)

    @property
    def center(self):
        return self.x + self.W / 2, self.y + self.H / 2

    # ---------- physics
    def physics(self, dt, move, jet):
        mult = 1.0
        if self.st['slow'] > 0:
            mult *= 0.45
        if self.st['haste'] > 0:
            mult *= 1.5
        if self.st['stun'] > 0:
            mult *= 0.35
        self.vx = move * RUN_SPEED * mult + self.kx
        self.kx *= max(0.0, 1 - 4.5 * dt)
        if jet and self.fuel > 0:
            self.vy -= JET_THRUST * dt
            self.vy = max(self.vy, -MAX_RISE)
            self.fuel = max(0, self.fuel - 38 * dt)
        else:
            self.fuel = min(100, self.fuel + (45 if self.on_ground else 8) * dt)
        self.vy = max(-1500, min(self.vy + GRAVITY * dt, MAX_FALL))

        old_x = self.x
        # Smooth gait clock: advances with actual horizontal movement, not frame rate.
        if abs(self.vx) > 12:
            self.anim_phase += dt * min(18.0, abs(self.vx) / 15.0)
        else:
            self.anim_phase += dt * 1.5
        dist = max(abs(self.vx), abs(self.vy)) * dt
        n = int(dist // 10) + 1
        sdt = dt / n
        self.on_ground = False
        for _ in range(n):
            self.x += self.vx * sdt
            for p in platforms:
                if self.rect.colliderect(p):
                    if self.vx > 0:
                        self.x = p.left - self.W
                    elif self.vx < 0:
                        self.x = p.right
                    self.kx *= 0.3
            self.y += self.vy * sdt
            for p in platforms:
                if self.rect.colliderect(p):
                    if self.vy > 0:
                        self.y = p.top - self.H
                        self.on_ground = True
                    elif self.vy < 0:
                        self.y = p.bottom
                    self.vy = 0
        self.blocked = move != 0 and abs(self.x - old_x) < 0.1
        # High-contrast soil footprints/dust puffs. Ochre + brown remain visible
        # on green, grey, desert and industrial terrain instead of blending in.
        if self.on_ground and abs(self.vx) > 45 and not self.blocked:
            self.step_timer -= dt
            if self.step_timer <= 0:
                fx = self.x + self.W * (0.32 if int(self.anim_phase * 2) % 2 == 0 else 0.68)
                fy = self.y + self.H - 2
                soil = random.choice([(151, 91, 36), (190, 130, 42), (218, 164, 63), (120, 72, 31)])
                # A small, crisp boot-print mark plus a few lighter soil flecks.
                add_particle(fx, fy, random.uniform(-15, 15), random.uniform(-25, -8),
                             0.42, soil, random.choice([3, 4, 5]), 45)
                add_particle(fx + random.uniform(-3, 3), fy - 1, random.uniform(-20, 20),
                             random.uniform(-32, -10), 0.30, (224, 177, 83), 2, 35)
                self.step_timer = random.uniform(0.105, 0.16)
        else:
            self.step_timer = min(self.step_timer, 0.06)

    # ---------- weapons
    def shoot(self, new_press=True):
        s = self.slot
        d = s['d']
        rapid_mode = bool(self.is_player and HIGH_SPEED_MG)
        if self.cooldown > 0 or (s['rt'] > 0 and not rapid_mode) or self.st['stun'] > 0 or self.burst_left > 0:
            return False
        if s['ammo'] <= 0 and not rapid_mode:
            self.reload()
            return False
        if not d['auto'] and not new_press and not rapid_mode:
            return False
        # Rapid mode fires at a very high rate regardless of the selected gun's normal delay.
        self.fire_once()
        if d['burst'] > 1 and not rapid_mode:
            self.burst_left = d['burst'] - 1
            self.burst_t = 0.06
        self.cooldown = 0.045 if rapid_mode else d['delay']
        return True

    def fire_once(self):
        s = self.slot
        d = s['d']
        emit_sound(d.get('name', 'Assault Rifle'))
        if s['ammo'] <= 0:
            self.burst_left = 0
            return
        cx, cy = self.center
        ang = self.angle
        if not self.is_player:
            ang += random.uniform(-0.05, 0.05)
        if self.st['blind'] > 0 and not self.is_player:
            ang += random.uniform(-0.6, 0.6)
        for _ in range(d['pellets']):
            a = ang + random.uniform(-d['spread'], d['spread'])
            projectiles.append(Projectile(cx + math.cos(a) * 26, cy + math.sin(a) * 26,
                                          a, self, d))
        if not (self.is_player and HIGH_SPEED_MG):
            s['ammo'] -= 1
        if d['recoil']:
            self.kx -= math.cos(ang) * d['recoil']
            self.vy -= math.sin(ang) * d['recoil'] * 0.3
        add_particle(cx + math.cos(ang) * 30, cy + math.sin(ang) * 30, 0, 0, 0.06,
                     (255, 240, 150), 4, 0)
        if s['ammo'] == 0 and not (self.is_player and HIGH_SPEED_MG):
            s['rt'] = d['reload']

    def reload(self):
        s = self.slot
        if s['rt'] <= 0 and s['ammo'] < s['d']['mag']:
            s['rt'] = s['d']['reload']

    def throw(self, tx, ty):
        if not self.throwables or self.throw_cd > 0 or not self.alive:
            return False
        self.tsel %= len(self.throwables)
        t = self.throwables[self.tsel]
        cx, cy = self.center
        dx, dy = tx - cx, ty - cy
        T = max(0.3, min(1.0, math.hypot(dx, dy) / 700))
        vx = dx / T + self.vx * 0.3
        vy = dy / T - 0.5 * 1200 * T
        sp = math.hypot(vx, vy)
        if sp > 1100:
            vx, vy = vx * 1100 / sp, vy * 1100 / sp
        grenades.append(Grenade(cx, cy - 6, vx, vy, t['d'], self))
        t['n'] -= 1
        if t['n'] <= 0:
            self.throwables.pop(self.tsel)
            self.tsel = 0
        self.throw_cd = 0.5 if self.is_player else 3.0
        return True

    def timers(self, dt):
        self.cooldown = max(0, self.cooldown - dt)
        self.throw_cd = max(0, self.throw_cd - dt)
        if self.immortal > 0 and not (self.is_player and TANK_MODE):
            self.immortal = max(0.0, self.immortal - dt)
        for s in self.slots:
            if s['rt'] > 0:
                s['rt'] -= dt
                if s['rt'] <= 0:
                    s['ammo'] = s['d']['mag']
        if self.burst_left > 0:
            self.burst_t -= dt
            if self.burst_t <= 0:
                self.fire_once()
                self.burst_left -= 1
                self.burst_t = 0.06
        for k in self.st:
            if self.st[k] > 0:
                self.st[k] = max(0.0, self.st[k] - dt)
        if self.st['burn'] > 0:
            hurt(self, 9 * dt, self.dot_owner, "Fire")
            if random.random() < 0.6:
                cx, cy = self.center
                add_particle(cx + random.uniform(-8, 8), cy + random.uniform(-10, 14), 0, -90,
                             0.4, (255, random.randint(90, 200), 30), 3, -50)
        if self.st['poison'] > 0:
            hurt(self, 5 * dt, self.dot_owner, "Poison")

    # ---------- drawing
    def draw(self, surf, cam):
        """Draw a compact military-soldier sprite using layered Pygame shapes."""
        r = self.rect.move(-cam[0], -cam[1])
        # Subtle body bounce and alternating stride create a smoother run cycle.
        moving = abs(self.vx) > 35 and self.on_ground
        gait = math.sin(self.anim_phase * 2.0)
        bob = int(round(abs(gait) * 2.0)) if moving else 0
        r.y -= bob
        # Soft contact shadow anchors the soldier to the terrain.
        shadow_x = int(self.x + self.W / 2 - cam[0])
        shadow_y = int(self.y + self.H - cam[1] + 1)
        shadow = pygame.Surface((42, 14), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (8, 12, 9, 92 if self.on_ground else 45), (0, 0, 42, 14))
        surf.blit(shadow, (shadow_x - 21, shadow_y - 6))
        if self.st['invis'] > 0:
            pygame.draw.rect(surf, (200, 220, 255), r, 1, border_radius=6)
            if not self.is_player:
                return

        # Team-specific tactical palette; bots now look like armored soldiers.
        if self.is_player:
            armor = (42, 91, 132)
            armor_light = (76, 135, 174)
            camo = (35, 74, 99)
            helmet = (42, 73, 91)
            visor = (100, 202, 225)
        else:
            team = getattr(self, 'team', 2)
            if team % 2 == 0:
                armor, armor_light, camo = (66, 78, 53), (105, 119, 72), (42, 54, 36)
                helmet, visor = (49, 60, 40), (161, 191, 122)
            else:
                armor, armor_light, camo = (87, 66, 48), (135, 103, 68), (53, 43, 34)
                helmet, visor = (57, 48, 39), (225, 177, 105)

        # Role-specific armor colors make each class visually identifiable.
        role = getattr(self, "role", "Assault")
        rd = BOT_ROLES.get(role, BOT_ROLES["Assault"])
        armor, armor_light, helmet, visor = rd["armor"], rd["light"], rd["helmet"], rd["visor"]
        camo = tuple(max(0, int(c * 0.62)) for c in armor)

        # Boots and legs: alternating knee/foot motion, with readable boot highlights.
        leg_y = r.y + 29
        stride = int(round(gait * 5)) if moving else 0
        lift_a = max(0, int(round(gait * 3))) if moving else 0
        lift_b = max(0, int(round(-gait * 3))) if moving else 0
        knee_bend = int(round(math.sin(self.anim_phase * 2.0 + 0.8) * 2)) if moving else 0
        left_knee = (r.centerx - 7 + stride, r.y + 34 + knee_bend)
        right_knee = (r.centerx + 7 - stride, r.y + 34 - knee_bend)
        left_foot = (r.centerx - 8 + stride * 2, r.bottom - 3 - lift_a + knee_bend)
        right_foot = (r.centerx + 8 - stride * 2, r.bottom - 3 - lift_b - knee_bend)
        pygame.draw.line(surf, (22, 24, 22), (r.centerx - 5, leg_y), left_knee, 6)
        pygame.draw.line(surf, (22, 24, 22), (r.centerx + 4, leg_y), right_knee, 6)
        pygame.draw.line(surf, armor_light, (r.centerx - 5, leg_y + 2), left_knee, 2)
        pygame.draw.line(surf, armor_light, (r.centerx + 4, leg_y + 2), right_knee, 2)
        pygame.draw.line(surf, (25, 27, 25), left_knee, left_foot, 5)
        pygame.draw.line(surf, (25, 27, 25), right_knee, right_foot, 5)
        pygame.draw.ellipse(surf, (17, 19, 18), (left_foot[0]-6, left_foot[1]-2, 12, 6))
        pygame.draw.ellipse(surf, (17, 19, 18), (right_foot[0]-6, right_foot[1]-2, 12, 6))
        pygame.draw.line(surf, (126, 111, 78), (left_foot[0]-3, left_foot[1]), (left_foot[0]+3, left_foot[1]), 1)
        pygame.draw.line(surf, (126, 111, 78), (right_foot[0]-3, right_foot[1]), (right_foot[0]+3, right_foot[1]), 1)

        # Backpack and armored torso
        pack_x = r.centerx - self.face * 10 - 4
        pygame.draw.rect(surf, (39, 45, 34), (pack_x, r.y + 13, 8, 15), border_radius=3)
        pygame.draw.rect(surf, camo, (pack_x + 1, r.y + 16, 6, 3), border_radius=1)
        torso = pygame.Rect(r.centerx - 9, r.y + 12, 18, 19)
        pygame.draw.rect(surf, armor, torso, border_radius=4)
        pygame.draw.rect(surf, armor_light, (torso.x + 2, torso.y + 2, 14, 4), border_radius=2)
        # Camouflage panels and chest rig
        for ox, oy, ww, hh in [(3, 8, 5, 3), (11, 7, 4, 4), (6, 13, 6, 3), (12, 15, 3, 3)]:
            pygame.draw.rect(surf, camo, (torso.x + ox, torso.y + oy - 1, ww, hh), border_radius=1)
        pygame.draw.rect(surf, (31, 35, 29), (r.centerx - 6, r.y + 18, 12, 8), border_radius=2)
        for k in range(3):
            pygame.draw.rect(surf, (174, 151, 89), (r.centerx - 4 + k * 4, r.y + 19, 2, 5), border_radius=1)
        # Shoulder armor and arms
        pygame.draw.circle(surf, armor_light, (r.centerx - 10, r.y + 15), 4)
        pygame.draw.circle(surf, armor_light, (r.centerx + 10, r.y + 15), 4)
        arm_swing = int(round(math.sin(self.anim_phase * 2.0 + math.pi) * 3)) if moving else 0
        pygame.draw.line(surf, armor, (r.centerx - 9, r.y + 16), (r.centerx - 5 + arm_swing, r.y + 24), 6)
        pygame.draw.line(surf, armor, (r.centerx + 9, r.y + 16), (r.centerx + 5 - arm_swing, r.y + 23), 6)
        pygame.draw.line(surf, armor_light, (r.centerx - 9, r.y + 16), (r.centerx - 5 + arm_swing, r.y + 21), 2)
        pygame.draw.line(surf, armor_light, (r.centerx + 9, r.y + 16), (r.centerx + 5 - arm_swing, r.y + 20), 2)
        pygame.draw.circle(surf, (184, 145, 105), (r.centerx - 5 + arm_swing, r.y + 24), 3)
        pygame.draw.circle(surf, (184, 145, 105), (r.centerx + 5 - arm_swing, r.y + 23), 3)

        # Neck, face, helmet, goggles and helmet rim
        pygame.draw.rect(surf, (139, 105, 77), (r.centerx - 4, r.y + 7, 8, 6), border_radius=2)
        pygame.draw.ellipse(surf, (174, 133, 99), (r.centerx - 8, r.y + 1, 16, 15))
        pygame.draw.arc(surf, (102, 75, 55), (r.centerx - 6, r.y + 4, 12, 9), 0.1, 3.0, 1)
        pygame.draw.ellipse(surf, helmet, (r.centerx - 10, r.y - 2, 20, 13))
        pygame.draw.rect(surf, helmet, (r.centerx - 12, r.y + 5, 24, 3), border_radius=2)
        pygame.draw.rect(surf, (24, 30, 29), (r.centerx - 7, r.y + 4, 14, 5), border_radius=2)
        pygame.draw.rect(surf, visor, (r.centerx - 6, r.y + 5, 12, 3), border_radius=1)
        pygame.draw.line(surf, armor_light, (r.centerx - 4, r.y + 1), (r.centerx + 4, r.y + 1), 2)
        # Class-specific helmet attachments and armor silhouettes.
        detail = rd["detail"] if not self.is_player else "standard"
        pygame.draw.line(surf, (24, 27, 25), (r.centerx - 7, r.y + 1), (r.centerx - 10, r.y - 5), 2)
        pygame.draw.circle(surf, (220, 195, 120), (r.centerx + 10, r.y + 15), 2)
        if detail == "scope":
            pygame.draw.rect(surf, (25, 30, 28), (r.centerx + 2, r.y + 15, 8, 5), border_radius=2)
            pygame.draw.circle(surf, (85, 230, 200), (r.centerx + 7, r.y + 17), 2)
            pygame.draw.line(surf, (48, 56, 45), (r.centerx - 11, r.y + 8), (r.centerx - 15, r.y + 17), 3)
        elif detail == "heavy":
            pygame.draw.rect(surf, (49, 49, 45), (r.centerx - 11, r.y + 12, 22, 18), 2, border_radius=4)
            pygame.draw.rect(surf, (150, 145, 123), (r.centerx - 10, r.y + 20, 4, 7))
            pygame.draw.rect(surf, (150, 145, 123), (r.centerx + 6, r.y + 20, 4, 7))
        elif detail == "night":
            pygame.draw.rect(surf, (18, 23, 27), (r.centerx - 9, r.y + 2, 18, 5), border_radius=2)
            pygame.draw.circle(surf, (45, 220, 255), (r.centerx - 4, r.y + 5), 2)
            pygame.draw.circle(surf, (45, 220, 255), (r.centerx + 4, r.y + 5), 2)
        elif detail == "ghost":
            pygame.draw.polygon(surf, (174, 185, 190), [(r.centerx - 10, r.y + 11), (r.centerx - 14, r.y + 25), (r.centerx - 7, r.y + 27)])
        elif detail == "engineer":
            pygame.draw.rect(surf, (39, 43, 32), (r.centerx - 13, r.y + 16, 5, 9), border_radius=1)
            pygame.draw.rect(surf, (39, 43, 32), (r.centerx + 8, r.y + 16, 5, 9), border_radius=1)
            pygame.draw.circle(surf, (240, 177, 62), (r.centerx + 10, r.y + 15), 3)
        elif detail == "camo":
            for ox, oy in [(-7, 14), (5, 20), (-4, 25), (7, 10)]:
                pygame.draw.ellipse(surf, (43, 67, 38), (r.centerx + ox, r.y + oy, 5, 3))
        elif detail == "shield":
            shield = [(r.centerx + self.face * 11, r.y + 13), (r.centerx + self.face * 18, r.y + 16), (r.centerx + self.face * 17, r.y + 28), (r.centerx + self.face * 11, r.y + 31)]
            pygame.draw.polygon(surf, (49, 53, 49), shield)
            pygame.draw.polygon(surf, (174, 162, 124), shield, 2)

        # Detailed weapon model: stock, receiver, barrel, sights, magazine and hands.
        # The weapon is drawn in a local coordinate system that follows the aim angle.
        cx, cy = r.centerx + math.cos(self.angle) * 5, r.y + 23 + math.sin(self.angle) * 2
        d = self.slot['d']
        cat = d.get('cat', 'Rifle')
        ln = GUN_LEN[cat] if d['type'] == 'gun' else 24
        ux, uy = math.cos(self.angle), math.sin(self.angle)
        px, py = -uy, ux
        def wp(along, side=0):
            return (int(cx + ux * along + px * side), int(cy + uy * along + py * side))
        def wpoly(points, color):
            pygame.draw.polygon(surf, color, [wp(a, b) for a, b in points])
        metal_dark = (17, 20, 21)
        metal = (55, 62, 61)
        metal_hi = (135, 145, 139)
        grip = (35, 31, 26)
        accent = d.get('color', (180, 190, 180))
        is_pistol = cat == 'Pistol'
        is_launcher = cat == 'Launcher'
        is_heavy = cat == 'LMG' or is_launcher
        body_start = 3 if is_pistol else 7
        body_end = ln * (0.57 if is_heavy else 0.62)
        # Rear stock / pistol grip.
        if not is_pistol:
            wpoly([(-7,-3), (body_start+3,-3), (body_start+3,3), (-6,3), (-9,1)], metal_dark)
            wpoly([(-5,-2), (body_start, -2), (body_start, 1), (-5,1)], (76, 83, 77))
        # Main receiver with upper rail and shaded lower edge.
        body_half = 4.5 if is_heavy else 3.4 if not is_pistol else 2.7
        wpoly([(body_start,-body_half), (body_end,-body_half), (body_end+2,-1),
               (body_end+1,body_half), (body_start,body_half)], metal_dark)
        wpoly([(body_start+1,-body_half+1), (body_end,-body_half+1),
               (body_end,0), (body_start+1,0)], metal)
        wpoly([(body_start+2,0), (body_end,0), (body_end+1,body_half-1),
               (body_start+2,body_half-1)], (39, 45, 43))
        # Barrel and muzzle, visibly separate from the receiver.
        barrel_start = body_end - 1
        barrel_end = ln - (3 if is_heavy else 1)
        barrel_half = 2.2 if is_heavy else 1.35
        wpoly([(barrel_start,-barrel_half-1), (barrel_end,-barrel_half),
               (barrel_end,barrel_half), (barrel_start,barrel_half+1)], metal_dark)
        wpoly([(barrel_start+1,-barrel_half), (barrel_end-2,-barrel_half+0.4),
               (barrel_end-2,0), (barrel_start+1,0)], metal_hi)
        wpoly([(barrel_end-2,-barrel_half-2), (barrel_end+2,-barrel_half-2),
               (barrel_end+2,barrel_half+2), (barrel_end-2,barrel_half+2)], (12, 15, 16))
        pygame.draw.circle(surf, (5, 7, 8), wp(barrel_end+1), 1 if not is_heavy else 2)
        # Magazine / feed drum, angled slightly backward from the receiver.
        if not is_pistol and cat not in ('Launcher', 'Energy'):
            mag_top = body_end * 0.56
            mag_len = 7 if cat == 'LMG' else 6
            wpoly([(mag_top,-1), (mag_top+4,-1), (mag_top+3,mag_len),
                   (mag_top,mag_len+1), (mag_top-1,2)], metal_dark)
            wpoly([(mag_top+1,0), (mag_top+3,0), (mag_top+2,mag_len-1),
                   (mag_top+1,mag_len-1)], (91, 99, 88))
            if cat == 'LMG':
                pygame.draw.circle(surf, (90, 94, 81), wp(mag_top+3, 4), 4)
        elif is_pistol:
            wpoly([(body_start+3,1), (body_start+7,1), (body_start+9,7),
                   (body_start+5,8)], grip)
        # Top rail, rear/front sights, and optional optic.
        if not is_pistol:
            wpoly([(body_start+2,-body_half-2), (body_end-1,-body_half-2),
                   (body_end-1,-body_half), (body_start+2,-body_half)], (20, 23, 23))
            wpoly([(body_start+4,-body_half-4), (body_start+6,-body_half-4),
                   (body_start+6,-body_half-1), (body_start+4,-body_half-1)], metal_hi)
            wpoly([(body_end-3,-body_half-4), (body_end-1,-body_half-4),
                   (body_end-1,-body_half-1), (body_end-3,-body_half-1)], metal_hi)
        if cat == 'Sniper':
            wpoly([(body_start+5,-body_half-5), (body_end-2,-body_half-5),
                   (body_end-2,-body_half-2), (body_start+5,-body_half-2)], (23, 28, 29))
            pygame.draw.circle(surf, (90, 190, 180), wp((body_start+body_end)/2, -body_half-4), 2)
            pygame.draw.circle(surf, (9, 13, 14), wp((body_start+body_end)/2, -body_half-4), 1)
        elif is_launcher:
            # Oversized launcher tube and rear cap for a distinct silhouette.
            wpoly([(body_start,-6), (ln-2,-6), (ln-2,6), (body_start,6)], (32, 39, 38))
            wpoly([(body_start+2,-4), (ln-4,-4), (ln-4,0), (body_start+2,0)], (98, 107, 96))
            wpoly([(ln-3,-7), (ln+1,-7), (ln+1,7), (ln-3,7)], (18, 21, 22))
        elif cat == 'LMG':
            # Heat shield slots along heavy gun barrel.
            for slot_pos in range(int(body_end+3), int(ln-6), 5):
                pygame.draw.line(surf, (18, 22, 22), wp(slot_pos,-2), wp(slot_pos,2), 1)
        # Hands visibly wrap the foregrip and rear grip, on top of the weapon.
        hand_a = wp(max(5, body_end*0.43), 4)
        hand_b = wp(max(2, body_start+1), -3)
        pygame.draw.circle(surf, (177, 132, 96), hand_a, 3)
        pygame.draw.circle(surf, (205, 160, 119), (hand_a[0]-1, hand_a[1]-1), 1)
        pygame.draw.circle(surf, (177, 132, 96), hand_b, 3)
        pygame.draw.circle(surf, (205, 160, 119), (hand_b[0]-1, hand_b[1]-1), 1)
        # Subtle colored weapon indicator, rather than a huge colored muzzle dot.
        if d.get('style') in ('laser', 'plasma'):
            pygame.draw.circle(surf, accent, wp(ln+2), 2)

        # Jetpack exhaust, status effects, and health bar
        jx = r.centerx - self.face * 16
        pygame.draw.rect(surf, (42, 47, 43), (jx - 4, r.y + 14, 8, 15), border_radius=2)
        pygame.draw.rect(surf, (109, 112, 96), (jx - 2, r.y + 16, 4, 9), border_radius=1)
        if not self.on_ground and self.vy < 0:
            pygame.draw.polygon(surf, (255, random.randint(120, 200), 40),
                                [(jx - 4, r.y + 29), (jx + 4, r.y + 29),
                                 (jx, r.y + 29 + random.randint(10, 20))])
        if self.st['slow'] > 0:
            pygame.draw.rect(surf, (150, 220, 255), r, 2, border_radius=6)
        if self.st['poison'] > 0:
            pygame.draw.rect(surf, (110, 230, 60), r, 2, border_radius=6)
        if self.st['haste'] > 0:
            pygame.draw.rect(surf, (255, 230, 90), r, 2, border_radius=6)
        if self.immortal > 0:
            pygame.draw.rect(surf, (255, 215, 0), r, 3, border_radius=6)
            pygame.draw.rect(surf, (255, 255, 180), r.inflate(4, 4), 1, border_radius=7)
        if self.st['stun'] > 0:
            t = pygame.time.get_ticks() / 1000
            pygame.draw.circle(surf, (255, 255, 0),
                               (r.centerx + int(math.cos(t * 8) * 12), r.y - 8), 3)
        if not self.is_player:
            pygame.draw.rect(surf, (45, 20, 18), (r.x - 4, r.y - 14, 32, 5), border_radius=2)
            pygame.draw.rect(surf, (80, 220, 90), (r.x - 4, r.y - 14, 32 * self.hp / 100, 5), border_radius=2)
            tag_font = pygame.font.Font(None, 13)
            tag = tag_font.render(role.upper(), True, (225, 232, 218))
            surf.blit(tag, (r.centerx - tag.get_width() // 2, r.y - 27))


# ====================================================================
#                    SPG COMMANDO ESCORT SQUAD
# ====================================================================
def deploy_spg_commandos(player):
    """Summon six elite escorts; they stay on the player's team and follow."""
    global spg_commandos
    # Avoid creating duplicates if B is tapped repeatedly.
    if len(spg_commandos) == 6 and all(f in everyone for f in spg_commandos):
        feed_add("SPG commandos already deployed — squad is protecting you!")
        return
    palette = [(52, 91, 62), (61, 103, 70), (46, 78, 57),
               (72, 94, 62), (48, 85, 72), (77, 100, 67)]
    spg_commandos = []
    for i in range(6):
        c = Fighter(palette[i], name=f"SPG Commando {i+1}", role="Ranger")
        c.team = player.team
        c.is_commando = True
        c.x = max(20, min(WORLD_W - c.W - 20, player.x + (i - 2.5) * 42))
        c.y = player.y - (i % 2) * 12
        c.spawn()
        c.x = max(20, min(WORLD_W - c.W - 20, player.x + (i - 2.5) * 42))
        c.y = player.y - (i % 2) * 12
        c.team = player.team
        c.is_commando = True
        spg_commandos.append(c)
        if c not in everyone:
            everyone.append(c)
    feed_add("SPG ELITE SQUAD DEPLOYED — 6 commandos following and protecting you!")


def commando_ai(commando, player, dt, index):
    """Keep a loose formation around the player while firing accurately at enemies."""
    if not commando.alive or not player.alive:
        return
    bx, by = commando.center
    # Six staggered escort positions around/behind the player.
    side = -1 if index % 2 == 0 else 1
    slot_x = player.x - player.face * (58 + (index // 2) * 24) + side * 20
    slot_y = player.y + (index % 3) * 18
    dx_follow, dy_follow = slot_x - commando.x, slot_y - commando.y
    move, jet = 0, False
    if abs(dx_follow) > 28:
        move = 1 if dx_follow > 0 else -1
    if dy_follow < -55 or (commando.blocked and abs(dx_follow) > 15):
        jet = True
    # Select nearest living enemy (never target player or squadmates).
    target, best = None, float("inf")
    for candidate in everyone:
        if candidate is commando or not candidate.alive:
            continue
        if getattr(candidate, "team", 0) == commando.team:
            continue
        dist2 = (candidate.center[0] - bx) ** 2 + (candidate.center[1] - by) ** 2
        if dist2 < best:
            target, best = candidate, dist2
    if target:
        tx, ty = target.center
        dx, dy = tx - bx, ty - by
        dist = math.hypot(dx, dy) or 1
        commando.angle = math.atan2(dy, dx)
        commando.face = 1 if dx > 0 else -1
        commando.target = target
        commando.retarget = 0.2
        # Ranger's accurate rifle: low spread, reliable controlled fire.
        if dist < 850 and line_of_sight((bx, by), (tx, ty)) and commando.cooldown <= 0:
            commando.shoot(True)
            commando.cooldown = max(commando.cooldown, 0.10)
    if commando.fuel < 8:
        jet = False
    commando.physics(dt, move, jet)


# ====================================================================
#                                BOTS
# ====================================================================
def bot_ai(bot, dt):
    bx, by = bot.center
    bot.retarget -= dt
    t = bot.target
    if bot.retarget <= 0 or t is None or not t.alive:
        bot.retarget = 0.8
        t, bd = None, 1e12
        for f in everyone:
            if f is bot or not f.alive or getattr(f, "team", 0) == getattr(bot, "team", -1):
                continue
            dd = (f.center[0] - bx) ** 2 + (f.center[1] - by) ** 2
            if dd < bd:
                t, bd = f, dd
        bot.target = t
    if bot.slot['ammo'] <= 0 and bot.slots[1 - bot.cur]['ammo'] > 0:
        bot.swap()
    d = bot.slot['d']
    rng = min(700, d['speed'] * d['life'] * 0.8)
    pref = max(120, min(380, rng * 0.55))
    if d['radius']:
        pref = max(pref, d['radius'] * 1.4)
    move, jet = 0, False
    if t is not None:
        tx, ty = t.center
        dx, dy = tx - bx, ty - by
        dist = math.hypot(dx, dy) or 1
        hidden = t.st['invis'] > 0
        if hidden:
            bot.wander_t -= dt
            if bot.wander_t <= 0:
                bot.wander_t = random.uniform(0.8, 2.0)
                bot.wander_dir = random.choice((-1, 0, 1))
            move = bot.wander_dir
        else:
            if dist > pref * 1.25:
                move = 1 if dx > 0 else -1
            elif dist < pref * 0.6:
                move = -1 if dx > 0 else 1
            if dy < -70:
                jet = True
        if d['grav']:
            tf = dist / d['speed']
            dy -= 0.5 * d['grav'] * tf * tf
        bot.angle = math.atan2(dy, dx)
        bot.face = 1 if dx > 0 else -1
        visible = (not hidden) and line_of_sight((bx, by), (tx, ty))
        if visible and dist < rng and random.random() < 0.4:
            bot.shoot(True)
        if visible and 160 < dist < 540 and bot.throw_cd <= 0 and bot.throwables \
                and random.random() < 0.012:
            bot.throw(tx, ty)
    if bot.blocked and random.random() < 0.9:
        jet = True
    if bot.on_ground and random.random() < 0.004:
        jet = True
    if bot.fuel < 8:
        jet = False
    bot.physics(dt, move, jet)


# ====================================================================
#                          CRATES / PICKUPS
# ====================================================================
def spawn_crate():
    p = random.choice(platforms[4:])
    x = random.randint(p.left + 6, max(p.left + 6, p.right - 28))
    roll = random.random()
    pool = GUNS if roll < 0.55 else BOMBS if roll < 0.85 else SMOKES
    crates.append({'x': x, 'y': p.top - 22, 'd': random.choice(pool)})


def pickup(f, c):
    d = c['d']
    if d['type'] == 'gun':
        f.slots[f.cur] = new_slot(d)
    else:
        f.give_throwable(d, 2)
    if f.is_player:
        feed_add(f"Picked up {d['name']}")


# ====================================================================
#                               UI
# ====================================================================
def draw_bar(x, y, w, h, frac, color, label):
    pygame.draw.rect(screen, (30, 30, 30), (x, y, w, h), border_radius=4)
    pygame.draw.rect(screen, color, (x, y, w * max(0, frac), h), border_radius=4)
    pygame.draw.rect(screen, (255, 255, 255), (x, y, w, h), 1, border_radius=4)
    screen.blit(font.render(label, True, (255, 255, 255)), (x + w + 8, y - 3))


def draw_world_decor(cam):
    """Draw military outpost scenery in world coordinates for the scrolling map."""
    for item in WORLD_DECOR:
        kind, wx, wy, ww, hh = item
        x, y = int(wx - cam[0]), int(wy - cam[1])
        if x + ww < -80 or x > W + 80 or y + hh < -100 or y > H + 100:
            continue
        if kind == "building":
            pygame.draw.rect(screen, (48, 58, 62), (x, y, ww, hh), border_radius=4)
            pygame.draw.rect(screen, (105, 118, 121), (x, y, ww, 8))
            for wy2 in range(y + 22, y + hh - 12, 34):
                for wx2 in range(x + 12, x + ww - 10, 27):
                    pygame.draw.rect(screen, (116, 165, 178), (wx2, wy2, 12, 15), border_radius=2)
                    pygame.draw.line(screen, (42, 57, 62), (wx2 + 6, wy2), (wx2 + 6, wy2 + 15), 1)
        elif kind == "container":
            pygame.draw.rect(screen, (57, 91, 72), (x, y, ww, hh), border_radius=3)
            pygame.draw.rect(screen, (130, 151, 120), (x, y, ww, 5))
            for xx in range(x + 9, x + ww, 13):
                pygame.draw.line(screen, (36, 61, 49), (xx, y + 7), (xx, y + hh - 3), 2)
        elif kind == "tree":
            pygame.draw.rect(screen, (76, 61, 43), (x + ww//2 - 5, y + hh//2, 10, hh//2))
            pygame.draw.circle(screen, (39, 82, 53), (x + ww//2, y + hh//3), max(14, ww//2))
            pygame.draw.circle(screen, (54, 105, 62), (x + ww//2 - 9, y + hh//3 - 7), max(10, ww//3))
        elif kind == "watchtower":
            pygame.draw.rect(screen, (65, 73, 67), (x + ww//2 - 5, y + 45, 10, hh - 45))
            pygame.draw.rect(screen, (78, 90, 77), (x, y + 35, ww, 30), border_radius=3)
            pygame.draw.rect(screen, (145, 153, 127), (x + 5, y + 40, ww - 10, 8))
            pygame.draw.line(screen, (35, 45, 39), (x + ww//2, y + 5), (x + ww//2, y + 35), 4)
        elif kind == "bridge":
            pygame.draw.rect(screen, (74, 79, 77), (x, y, ww, hh))
            pygame.draw.rect(screen, (157, 154, 131), (x, y, ww, 4))
            for xx in range(x, x + ww, 36):
                pygame.draw.line(screen, (39, 49, 48), (xx, y + hh), (xx + 8, y + hh + 18), 3)
        elif kind == "ruin":
            pygame.draw.rect(screen, (80, 77, 67), (x, y, ww, hh), 4)
            pygame.draw.rect(screen, (80, 77, 67), (x, y, 18, hh))
            pygame.draw.rect(screen, (80, 77, 67), (x + ww - 18, y + 65, 18, hh - 65))
            pygame.draw.line(screen, (130, 120, 98), (x + 18, y + 65), (x + ww - 18, y + 65), 5)
        elif kind == "antenna":
            pygame.draw.line(screen, (66, 75, 77), (x + ww//2, y + hh), (x + ww//2, y), 4)
            pygame.draw.line(screen, (66, 75, 77), (x + ww//2 - 18, y + 25), (x + ww//2 + 18, y + 25), 3)
            pygame.draw.circle(screen, (220, 70, 50), (x + ww//2, y + 4), 4)
        elif kind in ("barricade", "sandbag"):
            col = (91, 91, 70) if kind == "sandbag" else (72, 76, 69)
            pygame.draw.rect(screen, col, (x, y + hh//2, ww, hh//2), border_radius=4)
            for xx in range(x + 6, x + ww, 17):
                pygame.draw.line(screen, (132, 128, 98), (xx, y + hh//2 + 3), (xx, y + hh - 3), 2)
        elif kind == "crater":
            pygame.draw.ellipse(screen, (37, 42, 39), (x, y + hh//2, ww, max(8, hh//3)))
            pygame.draw.ellipse(screen, (77, 75, 61), (x + 5, y + hh//2 + 3, max(5, ww - 10), max(4, hh//5)), 2)


def draw_background(cam):
    """Layered cinematic battlefield backdrop with parallax depth and terrain detail."""
    theme = MAPS[selected_map]
    sky = theme["sky"]
    ground = theme["ground"]
    # Smooth atmospheric sky gradient.
    for i in range(0, H, 2):
        t = i / max(1, H)
        col = tuple(clamp8(c * (1 - t * 0.28) + (c * 0.60 + 12) * t * 0.28) for c in sky)
        pygame.draw.line(screen, col, (0, i), (W, i))
        if i + 1 < H:
            pygame.draw.line(screen, col, (0, i + 1), (W, i + 1))

    # Soft sun / atmospheric glow. Off-screen circles are naturally clipped.
    sun_x = int(W * 0.78 - cam[0] * 0.035) % (W + 180) - 90
    sun_y = int(95 - cam[1] * 0.025)
    glow = pygame.Surface((190, 190), pygame.SRCALPHA)
    for radius, alpha in [(86, 10), (66, 14), (45, 22), (27, 34)]:
        pygame.draw.circle(glow, (255, 222, 160, alpha), (95, 95), radius)
    screen.blit(glow, (sun_x - 95, sun_y - 95))
    pygame.draw.circle(screen, (255, 226, 166), (sun_x, sun_y), 17)
    pygame.draw.circle(screen, (255, 240, 202), (sun_x - 4, sun_y - 4), 8)

    # Clouds drift at a separate parallax rate to create a sense of scale.
    for j in range(5):
        cx = int((j * 247 - cam[0] * 0.09 + 40) % (W + 260) - 130)
        cy = 65 + (j * 31) % 115 - int(cam[1] * 0.025)
        cloud_col = tuple(clamp8(c + 24) for c in sky)
        for ox, oy, rr in [(-25, 5, 17), (0, -5, 24), (25, 2, 18), (45, 8, 12)]:
            pygame.draw.circle(screen, cloud_col, (cx + ox, cy + oy), rr)

    # Three mountain / skyline layers, each moving at a different rate.
    for layer, (base_y, step, amp, speed, color) in enumerate([
        (H - 120, 95, 60, 0.10, (48, 66, 68)),
        (H - 82,  78, 45, 0.17, (37, 55, 53)),
        (H - 48,  66, 32, 0.25, (28, 43, 39)),
    ]):
        pts = [(-20, H + 10)]
        for k in range(-1, W // step + 3):
            x = k * step - int(cam[0] * speed) % step
            peak = base_y - (amp // 2) - ((k * 37 + layer * 19) % amp)
            pts.append((x, peak))
        pts.extend([(W + 20, H + 10), (-20, H + 10)])
        pygame.draw.polygon(screen, color, pts)

    # Far-off structures add readable military-world silhouettes.
    for i in range(12):
        bx = int((i * 137 - cam[0] * 0.20) % (W + 150) - 75)
        base = H - 45 - int(cam[1] * 0.035)
        bh = 32 + (i * 29 % 72)
        bw = 30 + (i % 3) * 12
        shade = (max(15, sky[0] // 2), max(22, sky[1] // 2), max(24, sky[2] // 2))
        pygame.draw.rect(screen, shade, (bx, base - bh, bw, bh))
        pygame.draw.rect(screen, tuple(clamp8(c + 16) for c in shade), (bx, base - bh, bw, 4))
        for wy in range(base - bh + 12, base - 6, 17):
            pygame.draw.rect(screen, (177, 164, 119), (bx + 6, wy, 5, 6))
            if bw > 40:
                pygame.draw.rect(screen, (177, 164, 119), (bx + bw - 12, wy, 5, 6))

    # Subtle atmospheric haze near the horizon.
    haze = pygame.Surface((W, 95), pygame.SRCALPHA)
    pygame.draw.rect(haze, (193, 177, 139, 20), (0, 0, W, 95))
    screen.blit(haze, (0, H - 145 - int(cam[1] * 0.04)))

    # Ground-side texture streaks scroll with the terrain; deterministic to avoid flicker.
    rng = random.Random(selected_map * 7919)
    for i in range(95):
        wx = rng.randint(0, WORLD_W)
        wy = rng.randint(820, 970)
        x = int((wx - cam[0] * 0.88) % (W + 40) - 20)
        y = int(wy - cam[1] * 0.82)
        if -4 <= y <= H + 4:
            tint = rng.choice([tuple(clamp8(c + 17) for c in ground),
                               tuple(clamp8(c - 14) for c in ground), (130, 91, 52)])
            pygame.draw.line(screen, tint, (x, y), (x + rng.randint(3, 15), y), 1)
    # Foreground grass / rubble silhouettes make the scene feel less flat.
    for i in range(42):
        x = int((i * 53 - cam[0] * 0.98) % (W + 40) - 20)
        y = H - 8 - int(cam[1] * 0.82) % 12
        col = (36, 54, 37) if i % 2 else (77, 72, 48)
        pygame.draw.line(screen, col, (x, y), (x + (i % 5 - 2), y - 5 - i % 5), 2)


def draw_open_world_minimap(player):
    """Compact tactical map showing the whole explorable battlefield."""
    mw, mh = 230, 58
    mx, my = W - mw - 14, H - mh - 44
    panel = pygame.Surface((mw, mh), pygame.SRCALPHA)
    panel.fill((9, 15, 20, 205))
    pygame.draw.rect(panel, (135, 164, 150, 220), (0, 0, mw, mh), 2, border_radius=5)
    for p in platforms:
        if p.y >= 940 or p.w > WORLD_W * 0.7:
            continue
        px = int(p.x / WORLD_W * mw)
        py = int(p.y / WORLD_H * mh)
        pw = max(2, int(p.w / WORLD_W * mw))
        ph = max(1, int(p.h / WORLD_H * mh))
        pygame.draw.rect(panel, (92, 112, 101, 210), (px, py, pw, ph))
    for f in everyone:
        if not f.alive:
            continue
        px = int(max(0, min(WORLD_W, f.center[0])) / WORLD_W * (mw - 4)) + 2
        py = int(max(0, min(WORLD_H, f.center[1])) / WORLD_H * (mh - 4)) + 2
        col = (70, 210, 255) if f is player else ((80, 230, 130) if f.team == player.team else (255, 80, 70))
        pygame.draw.circle(panel, col, (px, py), 3 if f is player else 2)
    screen.blit(panel, (mx, my))
    label = tiny.render("TACTICAL MAP", True, (220, 235, 225))
    screen.blit(label, (mx, my - 14))


def draw_hud(player):
    draw_bar(15, 15, 200, 18, player.hp / 100, (220, 50, 50), f"HP {int(player.hp)}")
    world_label = small.render(f"OPEN WORLD  |  {MAPS[selected_map]['name']}  |  {int(player.x)}m", True, (225, 238, 220))
    screen.blit(world_label, (W//2 - world_label.get_width()//2, 12))
    draw_bar(15, 40, 200, 12, player.fuel / 100, (80, 170, 255), "FUEL")
    s = player.slot
    d = s['d']
    if HIGH_SPEED_MG:
        txt = f"HIGH-SPEED MG  INFINITE AMMO  |  {d['name']}"
    elif s['rt'] > 0:
        txt = f"{d['name']}  RELOADING {s['rt']:.1f}s"
    else:
        txt = f"{d['name']}  {s['ammo']}/{d['mag']}"
    screen.blit(font.render(txt, True, (255, 220, 70) if HIGH_SPEED_MG else CAT_COLOR[d['cat']]), (15, 62))
    o = player.slots[1 - player.cur]
    screen.blit(small.render(f"[Q] {o['d']['name']}  {o['ammo']}/{o['d']['mag']}", True,
                             (210, 210, 210)), (15, 88))
    if player.throwables:
        i = player.tsel % len(player.throwables)
        t = player.throwables[i]
        screen.blit(small.render(
            f"[E/G] {t['d']['name']} x{t['n']}  ({i + 1}/{len(player.throwables)})", True,
            CAT_COLOR[t['d']['cat']]), (15, 108))
    else:
        screen.blit(small.render("No throwables - grab a crate or press TAB", True,
                                 (200, 200, 200)), (15, 108))
    y = 130
    if player.immortal > 0:
        screen.blit(small.render(f"IMMORTAL {player.immortal:.0f}s", True, (255, 215, 0)), (15, y))
        y += 17
    colors = dict(burn=(255, 140, 40), poison=(120, 230, 60), slow=(150, 220, 255),
                  stun=(255, 255, 80), blind=(255, 255, 255), haste=(255, 230, 90),
                  invis=(170, 170, 255))
    for k, v in player.st.items():
        if v > 0:
            screen.blit(small.render(f"{k.upper()} {v:.1f}", True, colors[k]), (15, y))
            y += 17
    rows = sorted(everyone, key=lambda f: -f.kills)
    for i, f in enumerate(rows):
        t = small.render(f"{f.name}  K{f.kills} D{f.deaths}", True,
                         (255, 255, 255) if f.is_player else (255, 190, 190))
        screen.blit(t, (W - t.get_width() - 15, 15 + i * 18))
    fy = 15 + len(rows) * 18 + 10
    for text, tm in feed:
        t = tiny.render(text, True, (255, 255, 255))
        t.set_alpha(clamp8(255 * min(1, tm)))
        screen.blit(t, (W - t.get_width() - 15, fy))
        fy += 15
    footer = "TAB arsenal | Q swap | E cycle | G throw | R reload | K infinite rapid-fire | I timed immortal | Z tank mode"
    screen.blit(tiny.render(footer, True, (255, 220, 90) if TANK_MODE else (255, 255, 255)), (15, H - 20))
    if TANK_MODE:
        tank_label = font.render("IMMORTAL TANK  |  LMB: INFINITE MG  |  RMB: INFINITE ROCKETS", True, (255, 230, 80))
        screen.blit(tank_label, (W // 2 - tank_label.get_width() // 2, 12))
    if not player.alive:
        t = big_font.render(f"You died! Respawn in {max(0, player.respawn_timer):.1f}s",
                            True, (255, 255, 255))
        screen.blit(t, (W / 2 - t.get_width() / 2, H / 2 - 40))
    if player.alive and player.st['stun'] > 0:
        t = font.render("STUNNED", True, (255, 255, 80))
        screen.blit(t, (W / 2 - t.get_width() / 2, 80))
    if player.alive and player.immortal > 0:
        t = font.render(f"IMMORTAL {player.immortal:.0f}s", True, (255, 215, 0))
        screen.blit(t, (W / 2 - t.get_width() / 2, 50))


TABS = [("GUNS 1-30", 0, 30), ("GUNS 31-60", 30, 60), ("BOMBS 61-85", 60, 85),
        ("SMOKES 86-100", 85, 100)]


def tab_rects():
    return [pygame.Rect(25 + i * 205, 55, 200, 36) for i in range(len(TABS))]


def menu_cells(tab):
    a, b = TABS[tab][1:]
    cells = []
    for k, i in enumerate(range(a, b)):
        cells.append((pygame.Rect(25 + (k % 5) * 195, 100 + (k // 5) * 68, 190, 63),
                      ITEMS[i], i))
    return cells


def draw_menu(mouse, tab, player):
    screen.fill((18, 20, 28))
    screen.blit(font.render("ARSENAL  -  L-click: primary gun | R-click: secondary gun | "
                            "bombs/smokes: +5 throwables | TAB/Esc: close", True,
                            (255, 255, 255)), (25, 18))
    for i, r in enumerate(tab_rects()):
        pygame.draw.rect(screen, (70, 90, 140) if i == tab else (38, 42, 58), r,
                         border_radius=6)
        pygame.draw.rect(screen, (255, 255, 255), r, 1, border_radius=6)
        t = small.render(TABS[i][0], True, (255, 255, 255))
        screen.blit(t, (r.centerx - t.get_width() // 2, r.centery - t.get_height() // 2))
    hover = None
    owned = [s['d'] for s in player.slots] + [t['d'] for t in player.throwables]
    for r, d, i in menu_cells(tab):
        over = r.collidepoint(mouse)
        if over:
            hover = d
        eq = any(d is o for o in owned)
        pygame.draw.rect(screen, (58, 64, 88) if over else (35, 38, 52), r, border_radius=6)
        pygame.draw.rect(screen, CAT_COLOR[d['cat']], r, 4 if eq else 2, border_radius=6)
        screen.blit(small.render(f"{i + 1}. {d['name']}", True, (255, 255, 255)),
                    (r.x + 8, r.y + 8))
        screen.blit(tiny.render(stat_line(d), True, CAT_COLOR[d['cat']]), (r.x + 8, r.y + 34))
    panel = pygame.Rect(25, 518, 950, 70)
    pygame.draw.rect(screen, (30, 34, 48), panel, border_radius=6)
    if hover:
        screen.blit(font.render(hover['name'], True, CAT_COLOR[hover['cat']]),
                    (panel.x + 12, panel.y + 8))
        screen.blit(small.render(stat_line(hover) + "   |   " + ", ".join(tags(hover)),
                                 True, (230, 230, 230)), (panel.x + 12, panel.y + 40))
    else:
        screen.blit(small.render("Hover an item to see details. Gold border = already equipped.",
                                 True, (170, 170, 190)), (panel.x + 12, panel.y + 25))


def menu_click(pos, button, tab, player):
    for i, r in enumerate(tab_rects()):
        if r.collidepoint(pos):
            return i
    if button in (1, 3):
        for r, d, i in menu_cells(tab):
            if r.collidepoint(pos):
                if d['type'] == 'gun':
                    slot = 0 if button == 1 else 1
                    player.slots[slot] = new_slot(d)
                    player.cur = slot
                else:
                    player.give_throwable(d, 5)
                    player.select_throwable(d)
    return tab


# ====================================================================
#                               MAIN
# ====================================================================
FEATURES_50 = ['Team-based matchmaking and selectable team roster', '2-team deathmatch', 'Team colors and player labels', 'Friendly-fire protection', 'Bot ally coordination', 'Enemy-only bot targeting', 'Team kill/death scoreboard', 'Custom participant names', 'Select each participant individually', 'Quick team-balance button', 'Random team assignment', 'Team roster capacity validation', 'Free-for-all mode option', 'Match duration setting', 'Kill target setting', 'Respawn timer system', 'Health bar HUD', 'Jetpack fuel meter', 'Dual weapon slots', 'Weapon swap controls', '100-item arsenal', 'Primary weapon selection', 'Secondary weapon selection', 'Throwable inventory', 'Weapon crate pickups', 'Random loadout generator', 'Reload timer feedback', 'Projectile spread', 'Burst-fire weapons', 'Homing projectiles', 'Piercing projectiles', 'Explosive projectiles', 'Cluster projectiles', 'Ricochet projectiles', 'Status effects', 'Poison and burn effects', 'Slow and stun effects', 'Healing zones', 'Smoke visibility blockers', 'Teleport throwable', 'Timed grenades', 'Impact grenades', 'Sticky grenades', 'Proximity mines', 'Animated blast effects', 'Particle effects', 'Screen shake', 'Kill feed', 'Camera follow', 'Multi-platform arena']


def draw_team_setup(player, participants, selected):
    screen.fill((12, 18, 32))
    screen.blit(big_font.render("TEAM MATCHMAKING", True, (100, 220, 255)), (30, 18))
    screen.blit(small.render("Click a participant to switch Team 1 / Team 2. Press T to return.", True, (230,230,240)), (34, 72))
    screen.blit(font.render("TEAM 1  -  BLUE", True, (90, 170, 255)), (55, 112))
    screen.blit(font.render("TEAM 2  -  RED", True, (255, 110, 110)), (520, 112))
    left_y, right_y = 160, 160
    for i, f in enumerate(participants):
        team = getattr(f, "team", 1)
        col = (75, 135, 235) if team == 1 else (220, 75, 75)
        x = 55 if team == 1 else 520
        y = left_y if team == 1 else right_y
        rect = pygame.Rect(x, y, 410, 48)
        pygame.draw.rect(screen, (35, 45, 65), rect, border_radius=8)
        pygame.draw.rect(screen, col, rect, 3 if i == selected else 1, border_radius=8)
        label = f"{f.name}  {'(YOU)' if f.is_player else '(BOT)'}  | K {f.kills}  D {f.deaths}"
        screen.blit(small.render(label, True, (245,245,250)), (x+12, y+15))
        if team == 1: left_y += 60
        else: right_y += 60
    screen.blit(small.render("B = balance teams  |  R = random teams  |  ENTER = start/return", True, (255, 225, 130)), (55, H-35))


def apply_character_role(fighter, role):
    """Apply a selected soldier class to a participant and refresh its primary weapon."""
    if role not in BOT_ROLES:
        return
    fighter.role = role
    fighter.role_data = BOT_ROLES[role]
    weapon_name = fighter.role_data.get("gun", "Assault Rifle")
    if weapon_name not in BY_NAME:
        weapon_name = "Assault Rifle"
    fighter.slots[0] = new_slot(BY_NAME[weapon_name])
    fighter.cur = 0
    feed_add(f"{fighter.name}: {role} class equipped")


def draw_character_selection(participants, selected_index):
    """Selection screen: choose a participant, then click one of eight visual classes."""
    screen.fill((10, 15, 27))
    screen.blit(big_font.render("MILITARY CHARACTER LAB", True, (110, 220, 255)), (24, 12))
    screen.blit(small.render("1) Select a participant on the left.  2) Select a class card on the right.  C / Esc: close", True, (220, 230, 245)), (28, 65))
    screen.blit(font.render("PARTICIPANTS", True, (255, 215, 110)), (28, 105))
    screen.blit(font.render("CHOOSE VISUAL DESIGN / CLASS", True, (255, 215, 110)), (345, 105))
    for i, f in enumerate(participants):
        y = 145 + i * 78
        rect = pygame.Rect(25, y, 285, 64)
        team_color = (65, 130, 235) if f.team == 1 else (220, 80, 80)
        pygame.draw.rect(screen, (32, 42, 60), rect, border_radius=8)
        pygame.draw.rect(screen, (255, 220, 95) if i == selected_index else team_color, rect, 3 if i == selected_index else 1, border_radius=8)
        screen.blit(small.render(f.name + (" (YOU)" if f.is_player else ""), True, (245, 245, 250)), (rect.x+10, rect.y+8))
        screen.blit(tiny.render(f"Team {f.team}  |  {f.role}", True, (190, 205, 225)), (rect.x+10, rect.y+34))
    for i, role in enumerate(BOT_ROLE_NAMES):
        col, row = i % 2, i // 2
        rect = pygame.Rect(345 + col*310, 145 + row*105, 292, 88)
        rd = BOT_ROLES[role]
        active = participants[selected_index].role == role
        pygame.draw.rect(screen, (36, 44, 60), rect, border_radius=8)
        pygame.draw.rect(screen, (255, 215, 80) if active else rd["light"], rect, 3 if active else 2, border_radius=8)
        pygame.draw.ellipse(screen, rd["helmet"], (rect.x+14, rect.y+12, 28, 22))
        pygame.draw.rect(screen, rd["armor"], (rect.x+13, rect.y+34, 30, 35), border_radius=5)
        pygame.draw.rect(screen, rd["visor"], (rect.x+30, rect.y+21, 11, 5), border_radius=2)
        screen.blit(font.render(role, True, (245, 245, 250)), (rect.x+55, rect.y+13))
        screen.blit(tiny.render("Primary: " + rd["gun"], True, rd["light"]), (rect.x+55, rect.y+43))
        screen.blit(tiny.render("SELECTED" if active else "Click to equip", True, (255, 220, 110) if active else (185, 195, 210)), (rect.x+55, rect.y+63))
    screen.blit(tiny.render("Classes change armor colors, helmet/visor palette and primary weapon.", True, (175, 190, 210)), (28, H-24))


def draw_features():
    screen.fill((14, 18, 29))
    screen.blit(big_font.render("50 GAME FEATURES", True, (110, 225, 255)), (30, 18))
    for i, item in enumerate(FEATURES_50):
        col = i // 25
        row = i % 25
        txt = small.render(f"{i+1:02d}. {item}", True, (225, 230, 242))
        screen.blit(txt, (30 + col*490, 82 + row*19))
    screen.blit(small.render("F1 / Esc: close  |  T: teams  |  C: character designs", True, (255, 220, 120)), (30, H-25))



# =====================================================================
#                 DEPLOYABLE SUPPORT UNITS / STRIKES
# =====================================================================
def deploy_hunting_dog(owner):
    if not owner.alive:
        return
    owned = sum(1 for d in hunting_dogs if d['owner'] is owner)
    if owned >= 2:
        feed_add('Maximum 2 hunting dogs deployed!')
        return
    x, y = owner.center
    hunting_dogs.append({'x': x + owner.face * 35, 'y': y + 5, 'owner': owner,
                         'team': owner.team, 'hp': 65, 'bite_cd': 0.0, 'life': 35.0,
                         'vx': 0.0, 'anim': random.random() * 10})
    feed_add(f'{owner.name} deployed a hunting dog!')


def deploy_missile(owner, tx, ty):
    if not owner.alive:
        return
    tx, ty = max(25, min(WORLD_W - 25, tx)), max(25, min(WORLD_H - 25, ty))
    support_missiles.append({'x': tx, 'y': -40, 'tx': tx, 'ty': ty,
                             'owner': owner, 'team': owner.team, 'timer': 1.15,
                             'life': 1.15})
    feed_add('BGM SUPPORT MISSILE INCOMING!')



def deploy_fighter_jets(owner, tx, ty):
    """Call a three-plane friendly airstrike on the selected battlefield point."""
    if not owner.alive:
        return
    tx = max(100, min(WORLD_W - 100, tx))
    ty = max(120, min(WORLD_H - 100, ty))
    # Three aircraft arrive in a staggered formation from alternating directions.
    for idx in range(3):
        direction = 1 if idx != 1 else -1
        start_x = tx - direction * (620 + idx * 55)
        fighter_jets.append({
            'x': start_x, 'y': max(45, ty - 155 + idx * 42),
            'tx': tx, 'ty': ty, 'direction': direction,
            'owner': owner, 'team': owner.team, 'speed': 720 + idx * 35,
            'dropped': False, 'idx': idx, 'life': 4.0
        })
    feed_add('AIRSTRIKE INBOUND: 3 FIGHTER JETS!')


def _fighter_jet_bomb(jet):
    """Apply one team-safe airstrike blast at the selected target point."""
    x, y = jet['tx'], jet['ty']
    radius, damage = 155, 105
    for f in everyone:
        if not f.alive or f.team == jet['team']:
            continue
        fx, fy = f.center
        dist = math.hypot(fx - x, fy - y)
        if dist < radius:
            hurt(f, damage * (1 - 0.5 * dist / radius), jet['owner'], 'Fighter Jet')
            dx, dy = fx - x, fy - y
            length = math.hypot(dx, dy) or 1
            f.kx += dx / length * 300
            f.vy -= 160 * (1 - dist / radius)
    blasts.append([x, y, radius, 0.55, 0.55, (255, 135, 45)])
    for _ in range(42):
        a = random.uniform(0, math.tau)
        speed = random.uniform(90, 360)
        add_particle(x, y, math.cos(a) * speed, math.sin(a) * speed,
                     random.uniform(0.25, 0.75),
                     random.choice([(255, 180, 55), (255, 85, 35), (105, 105, 105)]),
                     random.randint(3, 7), 250)
    S['shake'] = max(S['shake'], 10)
    feed_add(f'Fighter jet {jet["idx"] + 1} strike!')


def deploy_turret(owner, tx, ty):
    if not owner.alive:
        return
    owned = sum(1 for t in auto_turrets if t['owner'] is owner)
    if owned >= 2:
        feed_add('Maximum 2 automatic turrets deployed!')
        return
    tx, ty = max(20, min(WORLD_W - 20, tx)), max(20, min(WORLD_H - 20, ty))
    # Snap the turret onto the nearest platform beneath the selected point.
    candidates = [pl for pl in platforms if pl.left <= tx <= pl.right and pl.top >= ty - 5]
    if candidates:
        pl = min(candidates, key=lambda pl: pl.top - ty if pl.top >= ty else 10**6)
        ty = pl.top - 17
    auto_turrets.append({'x': tx, 'y': ty, 'owner': owner, 'team': owner.team,
                         'hp': 130, 'cd': 0.2, 'life': 45.0, 'angle': 0.0})
    feed_add('Automatic machine-gun turret placed!')


def update_support_units(dt):
    # Hunting dogs sprint toward the closest living enemy and bite at close range.
    for dog in hunting_dogs[:]:
        dog['life'] -= dt
        dog['bite_cd'] = max(0.0, dog['bite_cd'] - dt)
        dog['anim'] += dt * 12
        owner = dog['owner']
        if dog['life'] <= 0 or dog['hp'] <= 0 or owner not in everyone:
            hunting_dogs.remove(dog)
            continue
        targets = [f for f in everyone if f.alive and f.team != dog['team']]
        if not targets:
            continue
        target = min(targets, key=lambda f: (f.center[0]-dog['x'])**2 + (f.center[1]-dog['y'])**2)
        tx, ty = target.center
        dx, dy = tx-dog['x'], ty-dog['y']
        dist = math.hypot(dx, dy) or 1
        dog['vx'] = max(-250, min(250, dx * 2.3))
        dog['x'] += dog['vx'] * dt
        # Keep the dog near the ground while allowing a small jump over ledges.
        dog['y'] += max(-100, min(100, dy * 1.3)) * dt
        dog['x'] = max(12, min(WORLD_W-12, dog['x']))
        dog['y'] = max(12, min(WORLD_H-20, dog['y']))
        if dist < 38 and dog['bite_cd'] <= 0:
            hurt(target, 13, owner, 'Hunting Dog')
            dog['bite_cd'] = 0.72
            for _ in range(5):
                add_particle(target.center[0], target.center[1], random.uniform(-70,70),
                             random.uniform(-90,20), 0.22, (230,190,130), 2, 100)

    # Fixed turrets scan for enemies and fire short, visible tracer rounds.
    for turret in auto_turrets[:]:
        turret['life'] -= dt
        turret['cd'] = max(0.0, turret['cd'] - dt)
        if turret['life'] <= 0 or turret['hp'] <= 0:
            auto_turrets.remove(turret)
            continue
        tx, ty = turret['x'], turret['y']
        candidates = [f for f in everyone if f.alive and f.team != turret['team']]
        candidates = [f for f in candidates if math.hypot(f.center[0]-tx, f.center[1]-ty) < 560]
        if candidates:
            target = min(candidates, key=lambda f: (f.center[0]-tx)**2 + (f.center[1]-ty)**2)
            ex, ey = target.center
            turret['angle'] = math.atan2(ey-(ty-8), ex-tx)
            if turret['cd'] <= 0 and line_of_sight((tx, ty-8), (ex, ey)):
                hurt(target, 7, turret['owner'], 'Auto Turret')
                turret['cd'] = 0.16
                add_particle(tx + math.cos(turret['angle'])*24, ty-8 + math.sin(turret['angle'])*24,
                             math.cos(turret['angle'])*70, math.sin(turret['angle'])*70,
                             0.12, (255,225,100), 3, 0)

    # Three fighter jets fly through the target area and release staggered bombs.
    for jet in fighter_jets[:]:
        jet['life'] -= dt
        jet['x'] += jet['direction'] * jet['speed'] * dt
        # After crossing the target, each plane releases its own strike.
        crossed = (jet['direction'] > 0 and jet['x'] >= jet['tx']) or (jet['direction'] < 0 and jet['x'] <= jet['tx'])
        if crossed and not jet['dropped']:
            jet['dropped'] = True
            _fighter_jet_bomb(jet)
        if jet['life'] <= 0 or (jet['dropped'] and abs(jet['x'] - jet['tx']) > 520):
            fighter_jets.remove(jet)

    # BGM-style support missile descends onto the selected world point, then explodes.
    for missile in support_missiles[:]:
        missile['timer'] -= dt
        progress = 1.0 - max(0.0, missile['timer']) / missile['life']
        missile['x'] = missile['tx']
        missile['y'] = -40 + (missile['ty'] + 40) * progress
        if random.random() < 0.8:
            add_particle(missile['x'] + random.uniform(-4,4), missile['y']-10,
                         random.uniform(-15,15), random.uniform(25,75), 0.25,
                         (255,150,55), 3, 0)
        if missile['timer'] <= 0:
            owner = missile['owner']
            # Team-safe blast: only enemies take damage; allies are not pushed either.
            x, y = missile['tx'], missile['ty']
            radius, damage = 145, 115
            for f in everyone:
                if not f.alive or f.team == missile['team']:
                    continue
                fx, fy = f.center
                dist = math.hypot(fx-x, fy-y)
                if dist < radius:
                    hurt(f, damage * (1 - 0.55 * dist / radius), owner, 'BGM Missile')
                    nx, ny = fx-x, fy-y
                    length = math.hypot(nx, ny) or 1
                    f.kx += nx/length * 280
                    f.vy -= abs(ny/length) * 180
            blasts.append([x, y, radius, 0.5, 0.5, (255,115,35)])
            for _ in range(60):
                a = random.uniform(0, math.tau)
                speed = random.uniform(80, 400)
                add_particle(x, y, math.cos(a)*speed, math.sin(a)*speed, random.uniform(.3,.8),
                             random.choice([(255,170,50),(255,90,30),(100,100,100)]),
                             random.randint(3,7), 250)
            S['shake'] = max(S['shake'], 14)
            feed_add('BGM missile impact!')
            support_missiles.remove(missile)


def draw_support_units(cam):
    # Dogs: animated ears, body and legs.
    for dog in hunting_dogs:
        x, y = int(dog['x']-cam[0]), int(dog['y']-cam[1])
        step = int(math.sin(dog['anim']) * 3)
        pygame.draw.ellipse(screen, (115,75,42), (x-13,y-9,27,16))
        pygame.draw.circle(screen, (145,98,55), (x+10,y-7), 8)
        pygame.draw.polygon(screen, (90,55,30), [(x+5,y-12),(x+4,y-21),(x+11,y-14)])
        pygame.draw.circle(screen, (15,15,15), (x+13,y-8), 2)
        pygame.draw.line(screen, (85,55,30), (x-8,y+2),(x-10-step,y+10), 3)
        pygame.draw.line(screen, (85,55,30), (x+5,y+2),(x+7+step,y+10), 3)
        pygame.draw.line(screen, (145,98,55), (x-12,y-3),(x-20,y-9), 3)
        pygame.draw.rect(screen, (30,30,30), (x-13,y-22,27,3))
        pygame.draw.rect(screen, (80,220,90), (x-13,y-22,27*max(0,dog['hp'])/65,3))
    # Turrets: base, rotating barrel and health indicator.
    for turret in auto_turrets:
        x, y = int(turret['x']-cam[0]), int(turret['y']-cam[1])
        pygame.draw.rect(screen, (55,65,78), (x-14,y-5,28,17), border_radius=3)
        pygame.draw.circle(screen, (155,170,185), (x,y-7), 10)
        ex = x + int(math.cos(turret['angle'])*27)
        ey = y-7 + int(math.sin(turret['angle'])*27)
        pygame.draw.line(screen, (45,50,58), (x,y-7), (ex,ey), 7)
        pygame.draw.line(screen, (220,225,230), (x,y-7), (ex,ey), 2)
        pygame.draw.rect(screen, (25,25,25), (x-16,y-22,32,4))
        pygame.draw.rect(screen, (80,220,100), (x-16,y-22,32*max(0,turret['hp'])/130,4))
    # Fighter jets: swept wings, fuselage, cockpit, tail fins and exhaust flame.
    for jet in fighter_jets:
        x, y = int(jet['x'] - cam[0]), int(jet['y'] - cam[1])
        d = jet['direction']
        # Exhaust flame trails behind the aircraft.
        tail_x = x - d * 28
        pygame.draw.line(screen, (255, 125, 35), (tail_x, y), (tail_x - d * 15, y), 5)
        pygame.draw.line(screen, (255, 220, 100), (tail_x, y), (tail_x - d * 9, y), 2)
        # Main fuselage and pointed nose.
        pygame.draw.polygon(screen, (105, 120, 135),
                            [(x + d*31, y), (x + d*12, y-5), (x - d*23, y-3),
                             (x - d*28, y), (x - d*23, y+3), (x + d*12, y+5)])
        # Swept wings and tailplanes.
        pygame.draw.polygon(screen, (65, 78, 92),
                            [(x + d*7, y), (x - d*7, y-17), (x - d*18, y-20),
                             (x - d*12, y-2), (x - d*5, y+2)])
        pygame.draw.polygon(screen, (65, 78, 92),
                            [(x + d*7, y), (x - d*7, y+17), (x - d*18, y+20),
                             (x - d*12, y+2), (x - d*5, y-2)])
        pygame.draw.polygon(screen, (80, 92, 106),
                            [(x - d*18, y), (x - d*26, y-9), (x - d*23, y), (x - d*26, y+9)])
        pygame.draw.ellipse(screen, (90, 190, 230), (x + d*5 - 5, y-3, 10, 6))
        pygame.draw.line(screen, (205, 215, 225), (x-d*10, y-2), (x+d*20, y-2), 1)

    # Missile and guidance marker.
    for missile in support_missiles:
        x, y = int(missile['x']-cam[0]), int(missile['y']-cam[1])
        pygame.draw.line(screen, (255,120,45), (x,y-12), (x,y+15), 4)
        pygame.draw.polygon(screen, (225,225,235), [(x,y+17),(x-6,y+7),(x+6,y+7)])
        pygame.draw.circle(screen, (255,90,45), (x,y+22), 5)
        tx, ty = int(missile['tx']-cam[0]), int(missile['ty']-cam[1])
        pygame.draw.circle(screen, (255,90,60), (tx,ty), 24, 2)
        pygame.draw.line(screen, (255,90,60), (tx-8,ty),(tx+8,ty),2)
        pygame.draw.line(screen, (255,90,60), (tx,ty-8),(tx,ty+8),2)

# =====================================================================
# ONLINE MULTIPLAYER (TCP state relay)
# Host one game and let friends connect using the host IP and port 50555.
# This synchronizes player movement/aim/team/class and visible firing state.
# It is a lightweight prototype, not a full authoritative game server.
# =====================================================================
class OnlineBattle:
    def __init__(self, mode, host="127.0.0.1", port=50555):
        self.mode, self.host, self.port = mode, host, port
        self.player_id = uuid.uuid4().hex[:8]
        self.peers = {}
        self.lock = threading.Lock()
        self.running = True
        self.sock = None
        if mode == "host":
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.bind(("0.0.0.0", port))
            self.sock.listen(8)
            threading.Thread(target=self._accept_loop, daemon=True).start()
        else:
            self.sock = socket.create_connection((host, port), timeout=8)
            self.sock.settimeout(None)
            threading.Thread(target=self._read_loop, args=(self.sock,), daemon=True).start()

    def _accept_loop(self):
        while self.running:
            try:
                conn, addr = self.sock.accept()
                conn.settimeout(None)
                with self.lock:
                    if not hasattr(self, "connections"): self.connections = []
                    self.connections.append(conn)
                threading.Thread(target=self._read_loop, args=(conn,), daemon=True).start()
            except OSError:
                break

    def _read_loop(self, conn):
        peer_id = None
        buffer = b""
        try:
            while self.running:
                chunk = conn.recv(4096)
                if not chunk: break
                buffer += chunk
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    try: data = json.loads(line.decode("utf-8"))
                    except (ValueError, UnicodeDecodeError): continue
                    peer_id = data.get("id", peer_id)
                    if peer_id and peer_id != self.player_id:
                        data["seen"] = time.time()
                        with self.lock: self.peers[peer_id] = data
                    if self.mode == "host": self._broadcast(line + b"\n", except_conn=conn)
        except OSError:
            pass
        finally:
            try: conn.close()
            except OSError: pass
            if self.mode == "host":
                with self.lock:
                    if hasattr(self, "connections") and conn in self.connections: self.connections.remove(conn)
            if peer_id:
                with self.lock: self.peers.pop(peer_id, None)

    def _broadcast(self, packet, except_conn=None):
        # Host relays the latest state to connected clients.
        with self.lock: conns = list(getattr(self, "connections", []))
        for c in conns:
            if c is except_conn: continue
            try: c.sendall(packet)
            except OSError: pass

    def send(self, state):
        data = dict(state, id=self.player_id, name="Friend-" + self.player_id[:4])
        packet = (json.dumps(data, separators=(",", ":")) + "\n").encode()
        if self.mode == "client":
            try: self.sock.sendall(packet)
            except OSError: pass
        else:
            # Host also stores its own state and relays it to clients.
            data["seen"] = time.time()
            with self.lock: self.peers[self.player_id] = data
            self._broadcast(packet)

    def close(self):
        self.running = False
        try: self.sock.close()
        except OSError: pass


# =====================================================================
#            BROWSER BRIDGE (frames out, keyboard / mouse in)
# =====================================================================
import argparse
import io
import queue
import http.server


def _parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--game", action="store_true")
    p.add_argument("--http-port", type=int, default=8765)
    p.add_argument("--bind", default="127.0.0.1")
    p.add_argument("--mode", default="offline", choices=["offline", "host", "join"])
    p.add_argument("--net-host", default="127.0.0.1")
    p.add_argument("--net-port", type=int, default=50555)
    return p.parse_args()


GAME_ARGS = _parse_args()

_KEYMAP = {"Space": pygame.K_SPACE, "Tab": pygame.K_TAB, "Escape": pygame.K_ESCAPE,
           "ArrowLeft": pygame.K_LEFT, "ArrowRight": pygame.K_RIGHT,
           "ArrowUp": pygame.K_UP, "ArrowDown": pygame.K_DOWN,
           "F1": pygame.K_F1, "F2": pygame.K_F2, "Enter": pygame.K_RETURN}
for _c in "abcdefghijklmnopqrstuvwxyz":
    _KEYMAP["Key" + _c.upper()] = getattr(pygame, "K_" + _c)


class _KeyState:
    def __init__(self):
        self.down = set()

    def __getitem__(self, k):
        return k in self.down


class _Bridge:
    def __init__(self):
        self.q = queue.Queue()
        self.keys = _KeyState()
        self.mouse = (W // 2, H // 2)
        self.btn = [False, False, False]
        self.cursor_visible = False
        self.frame = None
        self.ctype = "image/jpeg"
        self.fid = 0
        self.cond = threading.Condition()
        self.clients = 0
        self.use_jpeg = True

    # -- called from the game loop (main thread)
    def drain(self):
        out = []
        while True:
            try:
                ev = self.q.get_nowait()
            except queue.Empty:
                break
            t = ev.get("t")
            if t == "kd":
                k = _KEYMAP.get(ev.get("c"))
                if k is not None and k not in self.keys.down:
                    self.keys.down.add(k)
                    out.append(pygame.event.Event(pygame.KEYDOWN, key=k, mod=0,
                                                  unicode="", scancode=0))
            elif t == "ku":
                k = _KEYMAP.get(ev.get("c"))
                if k is not None:
                    self.keys.down.discard(k)
            elif t in ("mm", "md", "mu"):
                self.mouse = (int(ev.get("x", 0)), int(ev.get("y", 0)))
                b = int(ev.get("b", 1))
                if t == "md" and 1 <= b <= 3:
                    self.btn[b - 1] = True
                    out.append(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=self.mouse, button=b))
                elif t == "mu" and 1 <= b <= 3:
                    self.btn[b - 1] = False
            elif t == "wh":
                out.append(pygame.event.Event(pygame.MOUSEWHEEL, x=0, y=int(ev.get("d", 1)),
                                              flipped=False))
            elif t == "reset":
                self.keys.down.clear()
                self.btn = [False, False, False]
        return out

    def capture(self):
        if self.clients <= 0:
            return
        surf = pygame.display.get_surface()
        if surf is None:
            return
        data, ctype = None, "image/jpeg"
        if self.use_jpeg:
            try:
                buf = io.BytesIO()
                pygame.image.save(surf, buf, "frame.jpg")
                data = buf.getvalue()
            except Exception:
                self.use_jpeg = False
        if not data:
            buf = io.BytesIO()
            pygame.image.save(surf, buf, "frame.png")
            data, ctype = buf.getvalue(), "image/png"
        with self.cond:
            self.frame, self.ctype = data, ctype
            self.fid += 1
            self.cond.notify_all()


_bridge = _Bridge()
_sound_lock = threading.Lock()
_sound_events = []
_sound_next_id = 0

def emit_sound(name):
    """Queue a sound cue for the browser, which synthesizes audio locally."""
    global _sound_next_id
    try:
        with _sound_lock:
            _sound_next_id += 1
            _sound_events.append({"id": _sound_next_id, "name": str(name or "Assault Rifle")})
            # Keep memory bounded during long automatic-fire sessions.
            if len(_sound_events) > 160:
                del _sound_events[:len(_sound_events)-160]
    except Exception:
        pass

def get_sound_events(after_id):
    with _sound_lock:
        events = [e for e in _sound_events if e["id"] > after_id]
        return events[-40:], (_sound_events[-1]["id"] if _sound_events else after_id)

# Redirect pygame input queries and display flips to the bridge.
pygame.key.get_pressed = lambda: _bridge.keys
pygame.mouse.get_pos = lambda: _bridge.mouse
pygame.mouse.get_pressed = lambda *a, **k: tuple(_bridge.btn)


def _set_visible(v):
    _bridge.cursor_visible = bool(v)
    return True


pygame.mouse.set_visible = _set_visible
_real_flip = pygame.display.flip


def _flip_and_capture():
    _real_flip()
    _bridge.capture()


pygame.display.flip = _flip_and_capture


class _Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *args):
        pass

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Private-Network", "true")

    def _json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Content-Length", "0")
        self._cors()
        self.end_headers()

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"[]"
        try:
            events = json.loads(raw.decode("utf-8"))
            if isinstance(events, dict):
                events = [events]
            for ev in events:
                if isinstance(ev, dict):
                    _bridge.q.put(ev)
        except (ValueError, UnicodeDecodeError):
            return self._json(400, {"ok": False})
        self._json(200, {"ok": True, "cv": _bridge.cursor_visible})

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/sounds":
            try:
                from urllib.parse import urlparse, parse_qs
                query = parse_qs(urlparse(self.path).query)
                after_id = max(0, int(query.get("after", ["0"])[0]))
            except Exception:
                after_id = 0
            events, latest = get_sound_events(after_id)
            return self._json(200, {"events": events, "latest": latest})
        if path == "/stream":
            return self._stream()
        if path == "/frame":
            with _bridge.cond:
                data, ctype = _bridge.frame, _bridge.ctype
            if not data:
                return self._json(503, {"ok": False})
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self._cors()
            self.end_headers()
            self.wfile.write(data)
            return
        self._json(200, {"ok": True, "game": "mini-militia"})

    def _stream(self):
        self.send_response(200)
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close")
        self._cors()
        self.end_headers()
        self.close_connection = True
        last = -1
        _bridge.clients += 1
        try:
            while True:
                with _bridge.cond:
                    _bridge.cond.wait_for(lambda: _bridge.fid != last, timeout=5)
                    data, ctype, last = _bridge.frame, _bridge.ctype, _bridge.fid
                if not data:
                    continue
                head = ("--frame\r\nContent-Type: %s\r\nContent-Length: %d\r\n\r\n"
                        % (ctype, len(data))).encode()
                self.wfile.write(head + data + b"\r\n")
                self.wfile.flush()
        except OSError:
            pass
        finally:
            _bridge.clients -= 1


def _start_bridge():
    srv = http.server.ThreadingHTTPServer((GAME_ARGS.bind, GAME_ARGS.http_port), _Handler)
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    parent = os.getppid()

    def _watchdog():
        # Exit automatically when the Streamlit server (parent) goes away.
        while True:
            time.sleep(2)
            if os.getppid() != parent:
                os._exit(0)

    threading.Thread(target=_watchdog, daemon=True).start()



def main():
    global HIGH_SPEED_MG, TANK_MODE
    online = None
    _start_bridge()
    try:
        if GAME_ARGS.mode == "host":
            online = OnlineBattle("host", port=GAME_ARGS.net_port)
            print(f"Hosting on port {GAME_ARGS.net_port}.")
        elif GAME_ARGS.mode == "join":
            online = OnlineBattle("client", host=GAME_ARGS.net_host, port=GAME_ARGS.net_port)
            print("Connected! Starting battle...")
    except (OSError, ValueError) as exc:
        print(f"Online connection could not start: {exc}. Starting offline instead.")
        online = None

    player = Fighter((40, 110, 220), is_player=True, name="You")
    bots = [Fighter((200, 50, 50), name=f"Bot{i + 1}", role=BOT_ROLE_NAMES[i % len(BOT_ROLE_NAMES)])
            for i in range(NUM_BOTS)]
    for i, bot in enumerate(bots):
        bot.team = 2 if i % 2 == 0 else 1
    everyone[:] = [player] + bots
    apply_battlefield(0)
    for _ in range(6):
        spawn_crate()
    crate_timer = 4.0
    menu, tab = False, 0
    map_menu, map_page = False, 0
    team_menu, features_menu, selected_participant = False, False, 0
    character_menu, selected_character = False, 0
    fire_buf = 0.0
    running = True
    net_send_timer = 0.0

    while running:
        dt = min(clock.tick(60) / 1000, 0.033)
        pcx, pcy = player.center
        cam = [max(0, min(WORLD_W - W, pcx - W / 2)), max(0, min(WORLD_H - H, pcy - H / 2))]
        mouse = pygame.mouse.get_pos()

        for e in _bridge.drain():
            if e.type == pygame.QUIT:
                running = False
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    if menu or character_menu or map_menu:
                        menu = False
                        character_menu = False
                        map_menu = False
                    else:
                        pass  # web edition: use the Stop button to quit
                elif e.key == pygame.K_F2:
                    map_menu = not map_menu
                    menu = team_menu = character_menu = features_menu = False
                elif e.key == pygame.K_TAB:
                    menu = not menu
                elif e.key == pygame.K_t:
                    team_menu = not team_menu
                    character_menu = False
                    features_menu = False
                    menu = False
                elif e.key == pygame.K_c:
                    character_menu = not character_menu
                    team_menu = False
                    features_menu = False
                    menu = False
                    selected_character = max(0, min(selected_character, len(bots)))
                elif e.key == pygame.K_F1:
                    features_menu = not features_menu
                    team_menu = False
                    menu = False
                elif team_menu and e.key == pygame.K_b:
                    for idx, f in enumerate([player] + bots):
                        f.team = 1 if idx < (len(bots) + 1) // 2 else 2
                elif team_menu and e.key == pygame.K_r:
                    for f in [player] + bots:
                        f.team = random.choice((1, 2))
                elif not menu and not team_menu and e.key == pygame.K_b:
                    if player.alive:
                        deploy_spg_commandos(player)
                elif not menu and e.key == pygame.K_z:
                    # Toggle tank mode. Activation is immediate and persists through respawns.
                    TANK_MODE = not TANK_MODE
                    if TANK_MODE:
                        player.hp = 100
                        player.immortal = 10**9
                        player.cooldown = 0.0
                        player.throw_cd = 0.0
                        HIGH_SPEED_MG = True
                        feed_add("IMMORTAL TANK ON — left-click machine gun, right-click rockets!")
                    else:
                        player.immortal = 0.0
                        feed_add("Immortal tank mode OFF.")
                elif not menu and player.alive:
                    if e.key == pygame.K_r:
                        player.reload()
                    elif e.key == pygame.K_q:
                        player.swap()
                    elif e.key == pygame.K_e:
                        player.cycle_throwable()
                    elif e.key == pygame.K_g:
                        player.throw(mouse[0] + cam[0], mouse[1] + cam[1])
                    elif e.key == pygame.K_h:
                        deploy_hunting_dog(player)
                    elif e.key == pygame.K_m:
                        deploy_missile(player, mouse[0] + cam[0], mouse[1] + cam[1])
                    elif e.key == pygame.K_u:
                        deploy_turret(player, mouse[0] + cam[0], mouse[1] + cam[1])
                    elif e.key == pygame.K_j:
                        deploy_fighter_jets(player, mouse[0] + cam[0], mouse[1] + cam[1])
                    elif e.key == pygame.K_k:
                        HIGH_SPEED_MG = not HIGH_SPEED_MG
                        if HIGH_SPEED_MG:
                            player.slot['rt'] = 0.0
                            feed_add('HIGH-SPEED MACHINE GUN ON — INFINITE AMMO!')
                        else:
                            feed_add('High-speed machine gun disabled.')
                    elif e.key == pygame.K_n:
                        player.random_loadout()
                    elif e.key == pygame.K_i:
                        # Activate immortality for 2 minutes
                        player.immortal = 120.0
                        feed_add("IMMORTALITY activated for 2 minutes!")
            elif e.type == pygame.MOUSEWHEEL and not menu and player.alive:
                player.swap()
            elif e.type == pygame.MOUSEBUTTONDOWN:
                if map_menu and e.button == 1:
                    if pygame.Rect(35, 545, 160, 34).collidepoint(e.pos):
                        map_page = max(0, map_page - 1)
                    elif pygame.Rect(W-195, 545, 160, 34).collidepoint(e.pos):
                        map_page = min(3, map_page + 1)
                    else:
                        for slot, idx in enumerate(range(map_page*25, min(map_page*25+25, len(MAPS)))):
                            col, row = slot % 5, slot // 5
                            if pygame.Rect(32 + col*188, 125 + row*82, 176, 70).collidepoint(e.pos):
                                apply_battlefield(idx)
                                map_menu = False
                                feed_add(f"Battlefield selected: {MAPS[idx]['name']}")
                                break
                elif character_menu and e.button == 1:
                    participants = [player] + bots
                    for idx, f in enumerate(participants):
                        row_rect = pygame.Rect(25, 145 + idx * 78, 285, 64)
                        if row_rect.collidepoint(e.pos):
                            selected_character = idx
                            break
                    else:
                        for role_idx, role in enumerate(BOT_ROLE_NAMES):
                            col, row_idx = role_idx % 2, role_idx // 2
                            card = pygame.Rect(345 + col*310, 145 + row_idx*105, 292, 88)
                            if card.collidepoint(e.pos):
                                apply_character_role(participants[selected_character], role)
                                break
                elif team_menu and e.button == 1:
                    x, y = e.pos
                    participants = [player] + bots
                    # Rows map to roster order, allowing every participant to be selected.
                    left_y, right_y = 160, 160
                    for idx, f in enumerate(participants):
                        if f.team == 1:
                            x0, row_y = 55, left_y
                            left_y += 60
                        else:
                            x0, row_y = 520, right_y
                            right_y += 60
                        if x0 <= x <= x0 + 410 and row_y <= y <= row_y + 48:
                            f.team = 2 if f.team == 1 else 1
                            selected_participant = idx
                            break
                elif menu:
                    tab = menu_click(e.pos, e.button, tab, player)
                elif e.button == 1:
                    fire_buf = 0.18

        pygame.mouse.set_visible(menu or team_menu or features_menu or character_menu or map_menu)
        if map_menu:
            draw_map_selection()
            pygame.display.flip()
            continue
        if character_menu:
            draw_character_selection([player] + bots, selected_character)
            pygame.display.flip()
            continue
        if team_menu:
            draw_team_setup(player, [player] + bots, selected_participant)
            pygame.display.flip()
            continue
        if features_menu:
            draw_features()
            pygame.display.flip()
            continue
        if menu:
            draw_menu(mouse, tab, player)
            pygame.display.flip()
            continue

        keys = pygame.key.get_pressed()
        buttons = pygame.mouse.get_pressed()

        # ---------------- player input
        fire_buf = max(0.0, fire_buf - dt)
        if TANK_MODE:
            # Enforce tank state every frame so timed effects, respawns, and old state cannot cancel it.
            player.immortal = 10**9
            player.hp = 100
            player.alive = True
        if player.alive:
            move = (keys[pygame.K_d] or keys[pygame.K_RIGHT]) - (keys[pygame.K_a] or keys[pygame.K_LEFT])
            jet = keys[pygame.K_w] or keys[pygame.K_UP] or keys[pygame.K_SPACE]
            player.angle = math.atan2(mouse[1] + cam[1] - pcy, mouse[0] + cam[0] - pcx)
            if move:
                player.face = move
            player.physics(dt, move, jet)
            if TANK_MODE:
                # Tank's left-click super machine gun: very rapid, infinite ammunition.
                if buttons[0] and player.cooldown <= 0:
                    tank_mg = BY_NAME["Minigun"]
                    emit_sound("Minigun")
                    cx, cy = player.center
                    for _ in range(2):
                        a = player.angle + random.uniform(-0.035, 0.035)
                        projectiles.append(Projectile(cx + math.cos(a)*32, cy + math.sin(a)*32,
                                                      a, player, tank_mg))
                    player.cooldown = 0.035
                    for _ in range(3):
                        add_particle(cx + math.cos(player.angle)*36, cy + math.sin(player.angle)*36,
                                     random.uniform(-30,30), random.uniform(-30,30), 0.09,
                                     (255, 220, 90), 3, 0)
                # Tank's right-click rocket launcher: infinite rockets with blast damage.
                if len(buttons) > 2 and buttons[2] and player.throw_cd <= 0:
                    rocket = BY_NAME["Rocket Launcher"]
                    emit_sound("Rocket Launcher")
                    cx, cy = player.center
                    projectiles.append(Projectile(cx + math.cos(player.angle)*34,
                                                  cy + math.sin(player.angle)*34,
                                                  player.angle, player, rocket))
                    player.throw_cd = 0.24
            elif buttons[0] and player.shoot(fire_buf > 0):
                fire_buf = 0.0

        for b in bots:
            if b.alive:
                bot_ai(b, dt)
        for ci, commando in enumerate(spg_commandos):
            if commando in everyone and commando.alive:
                commando_ai(commando, player, dt, ci)

        update_support_units(dt)

        for f in everyone:
            if f.alive:
                f.timers(dt)
            else:
                f.respawn_timer -= dt
                if f.respawn_timer <= 0:
                    f.spawn()

        # ---------------- crates
        crate_timer -= dt
        if crate_timer <= 0:
            crate_timer = 5.0
            if len(crates) < 8:
                spawn_crate()
        for c in crates[:]:
            cr = pygame.Rect(c['x'], c['y'], 22, 22)
            for f in everyone:
                if f.alive and f.rect.colliderect(cr):
                    pickup(f, c)
                    crates.remove(c)
                    break

        # ---------------- world objects
        for pr in projectiles[:]:
            update_projectile(pr, dt)
            if pr.dead:
                projectiles.remove(pr)
        for g in grenades[:]:
            update_grenade(g, dt)
            if g.dead:
                grenades.remove(g)
        for z in zones[:]:
            update_zone(z, dt)
            if z.life <= 0:
                zones.remove(z)
        for s in scheduled[:]:
            s[0] -= dt
            if s[0] <= 0:
                scheduled.remove(s)
                s[1]()
        for p in particles:
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[3] += p[8] * dt
            p[4] -= dt
        particles[:] = [p for p in particles if p[4] > 0]
        for b in blasts[:]:
            b[3] -= dt
            if b[3] <= 0:
                blasts.remove(b)
        for f in feed[:]:
            f[1] -= dt
            if f[1] <= 0:
                feed.remove(f)
        S['shake'] *= 0.9

        # ---------------- online state exchange
        if online:
            net_send_timer -= dt
            if net_send_timer <= 0:
                net_send_timer = 1 / 20
                online.send({"x": float(player.center[0]), "y": float(player.center[1]),
                             "angle": float(player.angle), "hp": float(player.hp),
                             "team": int(getattr(player, "team", 1)),
                             "role": str(getattr(player, "role", "Assault")),
                             "alive": bool(player.alive), "shoot": bool(buttons[0]) if 'buttons' in locals() else False})
            # Remove stale peers after a short disconnect timeout.
            with online.lock:
                remote_states = [dict(v) for v in online.peers.values()
                                 if time.time() - v.get("seen", time.time()) < 8]

        # ---------------- draw
        sh = S['shake']
        dcam = [cam[0] + random.uniform(-sh, sh), cam[1] + random.uniform(-sh, sh)]
        draw_background(dcam)
        draw_world_decor(dcam)
        for p in platforms:
            r = p.move(-dcam[0], -dcam[1])
            pygame.draw.rect(screen, MAPS[selected_map]["ground"], r)
            pygame.draw.rect(screen, tuple(clamp8(c+35) for c in MAPS[selected_map]["ground"]), (r.x, r.y, r.w, min(8, r.h)))
        tt = pygame.time.get_ticks() / 1000
        for c in crates:
            r = pygame.Rect(c['x'] - dcam[0], c['y'] - dcam[1] + math.sin(tt * 3 + c['x']) * 2,
                            22, 22)
            col = CAT_COLOR[c['d']['cat']]
            pygame.draw.rect(screen, (45, 45, 55), r, border_radius=4)
            pygame.draw.rect(screen, col, r, 3, border_radius=4)
            lab = tiny.render(c['d']['name'], True, col)
            screen.blit(lab, (r.centerx - lab.get_width() // 2, r.y - 15))
        for g in grenades:
            draw_grenade(g, dcam)
        for f in everyone:
            if f.alive:
                f.draw(screen, dcam)
                if f is player and TANK_MODE and f.alive:
                    tr = pygame.Rect(int(f.x - dcam[0] - 20), int(f.y - dcam[1] + 7), 64, 32)
                    # Armoured hull, tracks, turret and barrel.
                    pygame.draw.rect(screen, (35, 65, 48), tr, border_radius=7)
                    pygame.draw.rect(screen, (95, 125, 78), tr.inflate(-8, -9), border_radius=5)
                    pygame.draw.rect(screen, (25, 30, 27), (tr.x+4, tr.bottom-5, tr.width-8, 9), border_radius=3)
                    for tx in range(tr.x+9, tr.right-5, 12):
                        pygame.draw.circle(screen, (145, 150, 130), (tx, tr.bottom-1), 4)
                    ux, uy = math.cos(f.angle), math.sin(f.angle)
                    cx, cy = tr.centerx, tr.centery-5
                    pygame.draw.circle(screen, (45, 55, 42), (cx, cy), 10)
                    pygame.draw.line(screen, (32, 40, 31), (cx, cy),
                                     (int(cx+ux*38), int(cy+uy*38)), 8)
                    pygame.draw.line(screen, (150, 170, 115), (cx, cy),
                                     (int(cx+ux*34), int(cy+uy*34)), 3)
        if online:
            for remote in remote_states:
                if not remote.get("alive", True):
                    continue
                rx, ry = int(remote.get("x", 0) - dcam[0]), int(remote.get("y", 0) - dcam[1])
                role = remote.get("role", "Assault")
                rd = BOT_ROLES.get(role, BOT_ROLES["Assault"])
                pygame.draw.rect(screen, rd["armor"], (rx - 11, ry - 13, 22, 27), border_radius=5)
                pygame.draw.circle(screen, rd["helmet"], (rx, ry - 19), 9)
                pygame.draw.rect(screen, rd["visor"], (rx - 6, ry - 21, 12, 4), border_radius=2)
                ang = float(remote.get("angle", 0))
                pygame.draw.line(screen, (35, 35, 35), (rx, ry),
                                 (int(rx + math.cos(ang) * 25), int(ry + math.sin(ang) * 25)), 5)
                if remote.get("shoot"):
                    pygame.draw.circle(screen, (255, 220, 90),
                                       (int(rx + math.cos(ang) * 31), int(ry + math.sin(ang) * 31)), 4)
                name_surf = tiny.render(str(remote.get("name", "Friend")), True, (255, 255, 255))
                screen.blit(name_surf, (rx - name_surf.get_width() // 2, ry - 38))
        draw_support_units(dcam)
        for pr in projectiles:
            draw_projectile(pr, dcam)
        for p in particles:
            pygame.draw.circle(screen, p[6], (int(p[0] - dcam[0]), int(p[1] - dcam[1])),
                               max(1, int(p[7] * p[4] / p[5] + 0.5)))
        fx_layer.fill((0, 0, 0, 0))
        for z in zones:
            draw_zone(z, dcam)
        for b in blasts:
            pr_ = 1 - b[3] / b[4]
            rad = int(b[2] * (0.3 + 0.7 * pr_))
            pos = (int(b[0] - dcam[0]), int(b[1] - dcam[1]))
            pygame.draw.circle(fx_layer, (*b[5], clamp8(200 * (1 - pr_))), pos, rad)
            pygame.draw.circle(fx_layer, (255, 255, 255, clamp8(255 * (1 - pr_))), pos, rad, 3)
        screen.blit(fx_layer, (0, 0))

        draw_hud(player)
        draw_open_world_minimap(player)
        support_hint = small.render('F2: Maps  |  B: 6 SPG Commandos  |  H: Dog  |  M: Missile  |  U: Turret  |  J: 3 Fighter Jets', True, (255, 225, 125))
        screen.blit(support_hint, (12, H-24))
        if player.alive and player.st['blind'] > 0:
            flash_surf.set_alpha(clamp8(255 * min(1.0, player.st['blind'] / 1.5)))
            screen.blit(flash_surf, (0, 0))

        # Mini-Militia-style dotted aiming guide: a continuous trail of bright dots
        # from the player's weapon direction to the mouse target.
        aim_start = (int(player.center[0] - dcam[0] + math.cos(player.angle) * 30),
                     int(player.center[1] - dcam[1] + math.sin(player.angle) * 30))
        ax, ay = aim_start
        bx, by = mouse
        line_len = math.hypot(bx - ax, by - ay)
        if line_len > 1:
            ux, uy = (bx - ax) / line_len, (by - ay) / line_len
            for distance in range(0, int(line_len), 11):
                px, py = int(ax + ux * distance), int(ay + uy * distance)
                # Softer, smaller dots so the guide does not obscure enemies.
                pygame.draw.circle(screen, (172, 169, 125), (px, py), 1)
        pygame.draw.circle(screen, (205, 210, 215), mouse, 4, 1)
        pygame.draw.circle(screen, (185, 165, 105), mouse, 1)

        pygame.display.flip()

    if online:
        online.close()
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
