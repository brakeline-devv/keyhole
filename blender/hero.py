"""Insider Radar hero: a faceted crystal spinning above a frosted white tower with stairs, coins and clouds,
on a soft lavender background (light, pastel 3D).
Headless:
  D:/blender.exe -b -P hero.py -- preview <frame> <out.png> [res_pct] [samples]
  D:/blender.exe -b -P hero.py -- render <out_dir/> [samples]
  D:/blender.exe -b -P hero.py -- save <file.blend>
Loop: LOOP frames at 30 fps, seamless (crystal turns 360 degrees, bob repeats twice).
"""
import bpy, bmesh, math, sys, random
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else ["save", "//hero.blend"]
MODE = argv[0]
FPS, LOOP = 30, 180
W, H = 1920, 1080
BG = (0.855, 0.846, 0.965)          # linear value of #eeedfb, the page background
SYMBOL_FONT = "C:/Windows/Fonts/seguibl.ttf"

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.fps = FPS
sc.frame_start, sc.frame_end = 0, LOOP - 1
random.seed(7)

# ---------------- materials ----------------
def node_mat(name):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    return m, nt, out

def frosted(name="frost"):
    """white matte that turns violet towards the bottom (world height), soft subsurface"""
    m, nt, out = node_mat(name)
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    geo = nt.nodes.new("ShaderNodeNewGeometry"); sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    mr = nt.nodes.new("ShaderNodeMapRange"); mr.inputs["From Min"].default_value = -3.7; mr.inputs["From Max"].default_value = -0.4
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.50, 0.42, 0.95, 1)
    ramp.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1)
    ramp.color_ramp.elements.new(0.42).color = (0.93, 0.92, 1.0, 1)
    nt.links.new(geo.outputs["Position"], sep.inputs[0])
    nt.links.new(sep.outputs["Z"], mr.inputs["Value"]); nt.links.new(mr.outputs["Result"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.6
    try:
        b.inputs["Subsurface Weight"].default_value = 0.25
        b.inputs["Subsurface Radius"].default_value = (0.4, 0.35, 0.6)
        b.inputs["Subsurface Scale"].default_value = 0.15
    except KeyError: pass
    nt.links.new(b.outputs[0], out.inputs[0])
    return m

def crystal_mat():
    m, nt, out = node_mat("crystal")
    glass = nt.nodes.new("ShaderNodeBsdfPrincipled")
    glass.inputs["Transmission Weight"].default_value = 0.22
    glass.inputs["Roughness"].default_value = 0.04
    glass.inputs["Coat Weight"].default_value = 1.0
    glass.inputs["IOR"].default_value = 1.45
    # colour follows the facet normal, so turning the crystal shifts blue -> violet -> pink
    geo = nt.nodes.new("ShaderNodeNewGeometry"); sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(geo.outputs["Normal"], sep.inputs[0])
    mr = nt.nodes.new("ShaderNodeMapRange"); mr.inputs["From Min"].default_value = -1; mr.inputs["From Max"].default_value = 1
    nt.links.new(sep.outputs["X"], mr.inputs["Value"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.03, 0.02, 0.55, 1)
    ramp.color_ramp.elements[1].color = (0.72, 0.45, 1.0, 1)
    ramp.color_ramp.elements.new(0.72).color = (0.12, 0.08, 0.95, 1)
    nt.links.new(mr.outputs["Result"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], glass.inputs["Base Color"])
    emit = nt.nodes.new("ShaderNodeEmission"); emit.inputs["Strength"].default_value = 0.8
    nt.links.new(ramp.outputs["Color"], emit.inputs["Color"])
    add = nt.nodes.new("ShaderNodeAddShader")
    nt.links.new(glass.outputs[0], add.inputs[0]); nt.links.new(emit.outputs[0], add.inputs[1])
    nt.links.new(add.outputs[0], out.inputs[0])
    return m

def simple(name, color, rough=0.35, metal=0.0, emit=0.0):
    m, nt, out = node_mat(name)
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if emit:
        b.inputs["Emission Color"].default_value = (*color, 1); b.inputs["Emission Strength"].default_value = emit
    nt.links.new(b.outputs[0], out.inputs[0])
    return m

def cloud_mat():
    m, nt, out = node_mat("cloud")
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    b.inputs["Base Color"].default_value = (1, 1, 1, 1); b.inputs["Roughness"].default_value = 0.9
    try:
        b.inputs["Subsurface Weight"].default_value = 0.6; b.inputs["Subsurface Radius"].default_value = (0.8, 0.8, 1.0); b.inputs["Subsurface Scale"].default_value = 0.2
    except KeyError: pass
    nt.links.new(b.outputs[0], out.inputs[0])
    return m

FROST, CRYSTAL = frosted(), crystal_mat()
SILVER = simple("silver", (0.82, 0.82, 0.90), rough=0.3, metal=0.35)
RIM = simple("rim", (0.42, 0.30, 1.0), rough=0.25, metal=0.4, emit=0.25)
VIOLET_COIN = simple("violetcoin", (0.30, 0.22, 1.0), rough=0.3, metal=0.3, emit=0.15)
DOME = simple("dome", (0.48, 0.40, 1.0), rough=0.4, emit=0.1)
SPARK = simple("spark", (1, 1, 1), emit=6)

# ---------------- helpers ----------------
def box(name, loc, size, mat=FROST, bevel=0.06):
    bpy.ops.mesh.primitive_cube_add(location=loc)
    o = bpy.context.object; o.name = name; o.scale = (size[0] / 2, size[1] / 2, size[2] / 2)
    bpy.ops.object.transform_apply(scale=True)
    if bevel:
        mod = o.modifiers.new("bev", "BEVEL"); mod.width = bevel; mod.segments = 4; mod.limit_method = "ANGLE"
    o.data.materials.append(mat)
    bpy.ops.object.shade_smooth()
    return o

def coin(name, loc, rot, r=0.55, t=0.12, face=SILVER, glyph="$"):
    bpy.ops.mesh.primitive_cylinder_add(vertices=96, radius=r, depth=t, location=(0, 0, 0))
    c = bpy.context.object; c.name = name
    mod = c.modifiers.new("bev", "BEVEL"); mod.width = 0.02; mod.segments = 3
    c.data.materials.append(face); c.data.materials.append(RIM)
    for p in c.data.polygons:
        if abs(p.normal.z) < 0.5: p.material_index = 1
    bpy.ops.object.shade_smooth()
    parts = [c]
    for side in (1, -1):
        bpy.ops.mesh.primitive_torus_add(major_radius=r * 0.72, minor_radius=0.012, location=(0, 0, side * t / 2))
        ring = bpy.context.object; ring.data.materials.append(face); parts.append(ring)
        if glyph:
            bpy.ops.object.text_add(location=(0, 0, side * t / 2))
            tx = bpy.context.object; tx.data.body = glyph; tx.data.align_x = "CENTER"; tx.data.align_y = "CENTER"
            try: tx.data.font = bpy.data.fonts.load(SYMBOL_FONT, check_existing=True)
            except Exception: pass
            tx.data.size = r * 0.95; tx.data.extrude = 0.012
            if side < 0: tx.rotation_euler = (0, math.pi, 0)
            tx.data.materials.append(face); parts.append(tx)
    root = bpy.data.objects.new(name + "_root", None); sc.collection.objects.link(root)
    for p in parts: p.parent = root
    root.location = loc; root.rotation_euler = rot
    return root

def cloud_mat():
    m, nt, out = node_mat("cloud")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    geo = nt.nodes.new("ShaderNodeTexCoord"); sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(geo.outputs["Object"], sep.inputs[0])
    mr = nt.nodes.new("ShaderNodeMapRange"); mr.inputs["From Min"].default_value = -0.45; mr.inputs["From Max"].default_value = 0.55
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.86, 0.85, 1.0, 1)
    ramp.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1)
    nt.links.new(sep.outputs["Z"], mr.inputs["Value"]); nt.links.new(mr.outputs["Result"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.75
    try:
        bsdf.inputs["Subsurface Weight"].default_value = 0.45; bsdf.inputs["Subsurface Radius"].default_value = (0.7, 0.7, 1.0); bsdf.inputs["Subsurface Scale"].default_value = 0.12
    except KeyError: pass
    nt.links.new(bsdf.outputs[0], out.inputs[0])
    return m
CLOUD = cloud_mat()
CLOUDS = []
def cloud(loc, s=1.0, seed=0):
    """5-7 round puffs (separate spheres, so each bump reads like the reference), parented to one empty"""
    rnd = random.Random(seed)
    root = bpy.data.objects.new("cloud", None); sc.collection.objects.link(root)
    puffs = [(0, 0, 0.12, 0.5), (0.52, 0.02, -0.04, 0.4), (-0.5, 0.04, -0.06, 0.38), (0.22, -0.08, 0.42, 0.36), (-0.2, 0.06, 0.34, 0.33),
             (0.86, 0.0, -0.2, 0.27), (-0.84, 0.02, -0.22, 0.25), (0.05, -0.3, -0.18, 0.36)]
    for x, y, z, r in puffs:
        bpy.ops.mesh.primitive_uv_sphere_add(segments=40, ring_count=20, radius=r * rnd.uniform(.93, 1.07), location=(x, y, z))
        o = bpy.context.object; o.data.materials.append(CLOUD); bpy.ops.object.shade_smooth(); o.parent = root
    root.location = loc; root.scale = (s, s, s * 0.9)
    CLOUDS.append((root, Vector(loc), rnd.uniform(0, 2 * math.pi)))
    return root

# ---------------- layout ----------------
# Positions measured on the reference (720x540), mapped to a 1920x1080 frame (x*2+480, y*2).
# At the tower's front face 1 unit = 150 px; the frame centre (960,540) looks at (TX, FACE_Y, TZ).
TX, TZ, FACE_Y, PX = -3.73, -0.07, -1.2, 150.0
def at(px, py, depth=0.0):
    """pixel position in the final frame -> world position (depth > 0 = further back)"""
    return Vector((TX + (px - 960) / PX, FACE_Y + depth, TZ - (py - 540) / PX))

# the tower: main block (top at z=0), right slab, blocks and stairs at its foot
bpy.ops.mesh.primitive_cylinder_add(vertices=160, radius=1.2, depth=7.0, location=(0, 0, -3.5))
tower = bpy.context.object; tower.name = "tower"
tb = tower.modifiers.new("bev", "BEVEL"); tb.width = 0.07; tb.segments = 5; tb.limit_method = "ANGLE"; tb.angle_limit = math.radians(60)
tower.data.materials.append(FROST); bpy.ops.object.shade_smooth()
try: tower.data.shade_smooth()
except Exception: pass
box("slab_r", (1.55, 0.35, -3.9), (0.66, 1.4, 7.0), bevel=0.1)
box("cap_r", (1.55, 0.35, -0.38), (0.72, 1.46, 0.1), bevel=0.03)
# Spiral staircase around the cylinder, fitted to the reference: theta is measured from the front (camera side)
# towards the left; each step turns 22 degrees and rises 0.3. The step at theta=31 deg is the one the big coin
# stands on (z -2.3), the three at 53/75/97 deg are the slabs climbing the left side (z -2.0/-1.7/-1.4).
fz = lambda py: TZ - (py - 540) / PX
fx = lambda px: TX + (px - 960) / PX
R_IN, R_OUT, STEP_DEG, RISE = 1.1, 2.05, 22.0, 0.3
def wedge(name, th0, th1, ztop, zbot=-7.5, seg=10):
    """an annular sector (a slice of ring) from the column out to R_OUT, solid down to the floor"""
    bm = bmesh.new()
    ring = []
    for k in range(seg + 1):
        t = math.radians(th0 + (th1 - th0) * k / seg)
        ring.append((-math.sin(t), -math.cos(t)))
    top_o = [bm.verts.new((R_OUT * x, R_OUT * y, ztop)) for x, y in ring]
    top_i = [bm.verts.new((R_IN * x, R_IN * y, ztop)) for x, y in ring]
    bot_o = [bm.verts.new((R_OUT * x, R_OUT * y, zbot)) for x, y in ring]
    bot_i = [bm.verts.new((R_IN * x, R_IN * y, zbot)) for x, y in ring]
    for k in range(seg):
        bm.faces.new((top_i[k], top_o[k], top_o[k + 1], top_i[k + 1]))
        bm.faces.new((bot_i[k + 1], bot_o[k + 1], bot_o[k], bot_i[k]))
        bm.faces.new((top_o[k], bot_o[k], bot_o[k + 1], top_o[k + 1]))
        bm.faces.new((top_i[k + 1], bot_i[k + 1], bot_i[k], top_i[k]))
    bm.faces.new((top_i[0], bot_i[0], bot_o[0], top_o[0]))
    bm.faces.new((top_o[-1], bot_o[-1], bot_i[-1], top_i[-1]))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); sc.collection.objects.link(o)
    mod = o.modifiers.new("bev", "BEVEL"); mod.width = 0.035; mod.segments = 3; mod.limit_method = "ANGLE"; mod.angle_limit = math.radians(40)
    o.data.materials.append(FROST)
    for pl in o.data.polygons: pl.use_smooth = True
    return o
SPANS = [(-68, -46), (-46, -24), (-24, -2), (-2, 20), (20, 42), (42, 64), (64, 100), (100, 122), (122, 144), (144, 166)]
STEPS = []
for i, (a0, a1) in enumerate(SPANS):
    z = -2.3 + (i - 4) * RISE
    wedge(f"step{i}", a0, a1, z)
    STEPS.append(((a0 + a1) / 2, z))
def on_step(i, out=1.55):
    th, z = STEPS[i]; t = math.radians(th)
    return Vector((-out * math.sin(t), -out * math.cos(t), z))
def tangent_yaw(i):
    """yaw that lays a standing coin along the step (its face looks along the radius)"""
    t = math.radians(STEPS[i][0])
    return math.atan2(math.sin(t), -math.cos(t))
bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=32, radius=0.52, location=(0.0, 0.35, -0.3))
dome = bpy.context.object; dome.data.materials.append(DOME); bpy.ops.object.shade_smooth()

# ---------------- coins ----------------
big = coin("coin_big", on_step(4, 1.62) + Vector((0, 0, 0.47 + 0.005)), (math.radians(90), 0, math.radians(28)), r=0.47, t=0.11, glyph="$")
rc = coin("coin_right", (1.55, 0.25, -0.33 + 0.46 + 0.005), (math.radians(90), 0, math.radians(-58)), r=0.46, t=0.1, face=VIOLET_COIN, glyph="$")
lc = coin("coin_left", on_step(6, 1.62) + Vector((0, 0, 0.42 + 0.005)), (math.radians(90), 0, tangent_yaw(6)), r=0.42, t=0.09, face=VIOLET_COIN, glyph="")

# ---------------- crystal ----------------
def crystal():
    bm = bmesh.new()
    n, rr = 6, 0.6
    top = bm.verts.new((0.06, 0.02, 1.42)); bot = bm.verts.new((-0.04, 0, -1.38))
    upper = [bm.verts.new((rr * math.cos(a) * (1 + 0.12 * math.sin(3 * a)), rr * 0.8 * math.sin(a), 1.02 + 0.07 * math.cos(2 * a))) for a in [i * 2 * math.pi / n for i in range(n)]]
    lower = [bm.verts.new((rr * 0.9 * math.cos(a + 0.12), rr * 0.76 * math.sin(a + 0.12), -0.62 + 0.05 * math.sin(2 * a))) for a in [i * 2 * math.pi / n for i in range(n)]]
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((upper[i], upper[j], top))
        bm.faces.new((lower[j], lower[i], bot))
        bm.faces.new((upper[i], lower[i], lower[j], upper[j]))
    me = bpy.data.meshes.new("crystal"); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new("crystal", me); sc.collection.objects.link(o)
    o.data.materials.append(CRYSTAL)
    return o
cry = crystal()
cry.scale = (0.84, 0.84, 0.8)
cry.rotation_euler = (math.radians(-6), math.radians(10), 0)
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.22, location=(0.0, 0.2, 0.62)); puff = bpy.context.object
puff.data.materials.append(simple("puff", (1, 1, 1), emit=7.0)); puff.scale = (0.9, 0.9, 0.4)
bpy.ops.object.light_add(type="POINT", location=(0.0, -0.2, 0.75)); glow = bpy.context.object
glow.data.energy = 18; glow.data.color = (0.88, 0.85, 1.0); glow.data.shadow_soft_size = 0.5
spin = bpy.data.objects.new("spin", None); sc.collection.objects.link(spin); cry.parent = spin
for f in range(LOOP + 1):
    sc.frame_set(f)
    spin.location = (-0.02, 0.2, 1.77 + 0.06 * math.sin(2 * math.pi * 2 * f / LOOP))
    spin.rotation_euler = (0, 0, 2 * math.pi * f / LOOP)
    spin.keyframe_insert("location"); spin.keyframe_insert("rotation_euler")
for fc in spin.animation_data.action.fcurves:
    for k in fc.keyframe_points: k.interpolation = "LINEAR"

# ---------------- clouds (pixel positions from the reference) ----------------
for i, (px, py, s, d) in enumerate([(960, 350, 0.55, 0), (1125, 640, 0.6, 0), (735, 880, 0.58, 0), (1790, 250, 0.55, 0.5), (1640, 760, 0.6, -0.9),
                                     (1180, 1075, 0.75, -1.6), (1560, 1095, 0.8, -1.8)]):
    cloud(at(px, py, d), s, seed=i)

for i in range(22):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=random.uniform(0.01, 0.022), location=at(random.uniform(1150, 1900), random.uniform(250, 1050), random.uniform(-1.5, 0.5)))
    bpy.context.object.data.materials.append(SPARK)

# coins: the big one rocks on its step edge, the violet one turns left/right, the top one wobbles
def wiggle(root, r, roll_deg=0.0, turn_deg=0.0, phase=0.0, period=90):
    """roll = the coin rocks in its own plane around the point touching the step (so it never sinks or floats);
    turn = it swivels around the vertical through that point"""
    base_loc, base_rot = root.location.copy(), root.rotation_euler.copy()
    contact = base_loc - Vector((0, 0, r))
    for f in range(0, LOOP + 1, 3):
        a = 2 * math.pi * f / period + phase
        roll = math.radians(roll_deg) * math.sin(a); turn = math.radians(turn_deg) * math.sin(a + 1.1)
        yaw = base_rot.z + turn
        side = Vector((math.cos(yaw), math.sin(yaw), 0))          # the disc's in-plane horizontal direction
        root.location = contact + Vector((0, 0, r * math.cos(roll))) + side * (r * math.sin(roll)) * 0.0
        root.rotation_euler = (base_rot.x, roll, yaw)
        root.keyframe_insert("location", frame=f); root.keyframe_insert("rotation_euler", frame=f)
    root.location, root.rotation_euler = base_loc, base_rot
wiggle(big, 0.47, roll_deg=4.0, turn_deg=6.0)          # balances on its step
wiggle(lc, 0.42, roll_deg=3.0, turn_deg=12.0, phase=0.4) # turns a little on its landing, clears both walls
wiggle(rc, 0.46, roll_deg=2.0, turn_deg=8.0, phase=2.1)

# clouds sway side to side and turn a little, period 90 frames (two cycles per loop, seamless)
for root, base, ph in CLOUDS:
    for f in range(0, LOOP + 1, 3):
        a = 2 * math.pi * 2 * f / LOOP + ph
        root.location = base + Vector((0.07 * math.sin(a), 0, 0.03 * math.sin(a + 1.3)))
        root.rotation_euler = (0, 0, math.radians(11) * math.sin(a + 0.6))
        root.keyframe_insert("location", frame=f); root.keyframe_insert("rotation_euler", frame=f)
    for fc in root.animation_data.action.fcurves:
        for k in fc.keyframe_points: k.interpolation = "BEZIER"

# ---------------- world, lights, camera ----------------
world = bpy.data.worlds.new("w"); sc.world = world; world.use_nodes = True
wn = world.node_tree.nodes; wl = world.node_tree.links
bg_cam = wn["Background"]; bg_cam.inputs[0].default_value = (*BG, 1); bg_cam.inputs[1].default_value = 1.0
bg_lit = wn.new("ShaderNodeBackground"); bg_lit.inputs[0].default_value = (0.86, 0.85, 0.99, 1); bg_lit.inputs[1].default_value = 0.55
lp = wn.new("ShaderNodeLightPath"); mix = wn.new("ShaderNodeMixShader")
wl.new(lp.outputs["Is Camera Ray"], mix.inputs[0]); wl.new(bg_lit.outputs[0], mix.inputs[1]); wl.new(bg_cam.outputs[0], mix.inputs[2])
wl.new(mix.outputs[0], wn["World Output"].inputs[0])

def area(loc, rot, size, energy, color=(1, 1, 1)):
    bpy.ops.object.light_add(type="AREA", location=loc, rotation=rot)
    l = bpy.context.object; l.data.size = size; l.data.energy = energy; l.data.color = color
    return l
area((-7, -8, 7), (math.radians(55), 0, math.radians(-40)), 10, 880)
area((7, -6, 1), (math.radians(80), 0, math.radians(50)), 7, 260, (0.82, 0.78, 1.0))
area((0, -5, -9), (math.radians(160), 0, 0), 10, 260, (0.55, 0.45, 1.0))

cam_data = bpy.data.cameras.new("cam"); cam_data.lens = 50; cam_data.sensor_width = 36
cam = bpy.data.objects.new("cam", cam_data); sc.collection.objects.link(cam); sc.camera = cam
DIST = 12.8 / (2 * (18 / 50))
cam.location = (TX, FACE_Y - DIST, TZ + 1.05)
cam.rotation_euler = (Vector((TX, FACE_Y, TZ)) - cam.location).to_track_quat("-Z", "Y").to_euler()

# ---------------- render settings ----------------
r = sc.render
r.resolution_x, r.resolution_y = W, H
r.engine = "CYCLES"
sc.cycles.samples = 96
sc.cycles.use_denoising = True
try:
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "OPTIX"; prefs.get_devices()
    for d in prefs.devices: d.use = True
    sc.cycles.device = "GPU"
except Exception as e: print("GPU setup failed, CPU:", e)
sc.view_settings.view_transform = "Standard"
sc.view_settings.look = "None"
sc.cycles.max_bounces = 8; sc.cycles.transmission_bounces = 8

sc.use_nodes = True
ct = sc.node_tree; ct.nodes.clear()
rl = ct.nodes.new("CompositorNodeRLayers"); gl = ct.nodes.new("CompositorNodeGlare"); co = ct.nodes.new("CompositorNodeComposite")
gl.glare_type = "FOG_GLOW"; gl.threshold = 1.6; gl.size = 9; gl.mix = -0.2
ct.links.new(rl.outputs["Image"], gl.inputs["Image"]); ct.links.new(gl.outputs["Image"], co.inputs["Image"])

if MODE == "preview":
    frame = int(argv[1]); outp = argv[2]
    pct = int(argv[3]) if len(argv) > 3 else 50
    if len(argv) > 4: sc.cycles.samples = int(argv[4])
    r.resolution_percentage = pct; sc.frame_set(frame)
    r.filepath = outp; r.image_settings.file_format = "PNG"
    bpy.ops.render.render(write_still=True)
elif MODE == "render":
    outd = argv[1]
    if len(argv) > 2: sc.cycles.samples = int(argv[2])
    r.image_settings.file_format = "JPEG"; r.image_settings.quality = 92
    r.filepath = outd + "f-"
    bpy.ops.render.render(animation=True)
else:
    bpy.ops.wm.save_as_mainfile(filepath=bpy.path.abspath(argv[1]))
