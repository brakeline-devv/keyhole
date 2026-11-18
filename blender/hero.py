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
    mr = nt.nodes.new("ShaderNodeMapRange"); mr.inputs["From Min"].default_value = -3.9; mr.inputs["From Max"].default_value = 0.1
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.36, 0.27, 0.92, 1)
    ramp.color_ramp.elements[1].color = (0.98, 0.975, 1.0, 1)
    ramp.color_ramp.elements.new(0.55).color = (0.80, 0.77, 0.98, 1)
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
    glass.inputs["Roughness"].default_value = 0.08
    glass.inputs["IOR"].default_value = 1.45
    # colour follows the facet normal, so turning the crystal shifts blue -> violet -> pink
    geo = nt.nodes.new("ShaderNodeNewGeometry"); sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(geo.outputs["Normal"], sep.inputs[0])
    mr = nt.nodes.new("ShaderNodeMapRange"); mr.inputs["From Min"].default_value = -1; mr.inputs["From Max"].default_value = 1
    nt.links.new(sep.outputs["X"], mr.inputs["Value"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.06, 0.04, 0.9, 1)
    ramp.color_ramp.elements[1].color = (0.85, 0.40, 1.0, 1)
    ramp.color_ramp.elements.new(0.7).color = (0.22, 0.15, 1.0, 1)
    nt.links.new(mr.outputs["Result"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], glass.inputs["Base Color"])
    emit = nt.nodes.new("ShaderNodeEmission"); emit.inputs["Strength"].default_value = 1.35
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
CLOUD = cloud_mat()
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

def cloud(loc, s=1.0, seed=0):
    rnd = random.Random(seed)
    mb = bpy.data.metaballs.new("cloud"); mb.resolution = 0.05; mb.render_resolution = 0.03; mb.threshold = 0.6
    o = bpy.data.objects.new("cloud", mb); sc.collection.objects.link(o)
    blobs = [(0, 0, 0.05, 0.6), (0.5, 0.05, -0.05, 0.46), (-0.5, 0.02, -0.08, 0.44), (0.18, -0.05, 0.42, 0.48), (-0.22, 0.05, 0.32, 0.42), (0.85, 0.02, -0.18, 0.34), (-0.85, 0, -0.2, 0.32), (0.0, -0.25, -0.12, 0.42)]
    for x, y, z, r in blobs:
        e = mb.elements.new(); e.co = (x + rnd.uniform(-.05, .05), y, z + rnd.uniform(-.04, .04)); e.radius = r * rnd.uniform(.92, 1.08)
    o.location = loc; o.scale = (s, s, s * 0.85)
    o.data.materials.append(CLOUD)
    return o

# ---------------- layout ----------------
# Positions measured on the reference (720x540), mapped to a 1920x1080 frame (x*2+480, y*2).
# At the tower's front face 1 unit = 150 px; the frame centre (960,540) looks at (TX, FACE_Y, TZ).
TX, TZ, FACE_Y, PX = -3.73, -0.07, -1.2, 150.0
def at(px, py, depth=0.0):
    """pixel position in the final frame -> world position (depth > 0 = further back)"""
    return Vector((TX + (px - 960) / PX, FACE_Y + depth, TZ - (py - 540) / PX))

# the tower: main block (top at z=0), right slab, blocks and stairs at its foot
box("tower", (0, 0, -3.5), (2.4, 2.4, 7.0))
box("slab_r", (1.55, 0.35, -3.9), (0.66, 1.4, 7.0))
box("cap_r", (1.55, 0.35, -0.38), (0.72, 1.46, 0.1), bevel=0.03)
box("side_l", (-1.45, 0.3, -2.4), (0.62, 1.6, 2.6))
box("ledge", (-1.05, -1.7, -2.6), (1.2, 1.0, 0.75))
for i in range(4):
    box(f"step{i}", (-0.25 + i * 0.5, -1.65 - i * 0.35, -3.05 - i * 0.32), (1.6, 1.3, 0.96), bevel=0.035)
box("plinth", (0.9, -3.3, -5.0), (5.0, 1.6, 1.4))
bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=32, radius=0.36, location=(0.0, 0.25, -0.2))
dome = bpy.context.object; dome.data.materials.append(DOME); bpy.ops.object.shade_smooth()

# ---------------- coins ----------------
coin("coin_big", (-0.87, -1.75, -1.79), (math.radians(90), 0, math.radians(14)), r=0.45, t=0.11, glyph="$")
coin("coin_right", (1.36, 0.0, 0.22), (math.radians(90), 0, math.radians(-46)), r=0.34, t=0.08, face=VIOLET_COIN, glyph="$")
coin("coin_left", (-1.42, -0.62, -0.87), (math.radians(90), 0, math.radians(80)), r=0.42, t=0.09, face=VIOLET_COIN, glyph="")

# ---------------- crystal ----------------
def crystal():
    bm = bmesh.new()
    n, rr = 7, 0.62
    top = bm.verts.new((0.05, 0.02, 1.55)); bot = bm.verts.new((-0.03, 0, -1.35))
    upper = [bm.verts.new((rr * math.cos(a) * (1 + 0.12 * math.sin(3 * a)), rr * 0.82 * math.sin(a), 0.62 + 0.08 * math.cos(2 * a))) for a in [i * 2 * math.pi / n for i in range(n)]]
    lower = [bm.verts.new((rr * 0.92 * math.cos(a + 0.3), rr * 0.78 * math.sin(a + 0.3), -0.55 + 0.06 * math.sin(2 * a))) for a in [i * 2 * math.pi / n for i in range(n)]]
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
cry.scale = (0.78, 0.78, 0.76)
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
for i, (px, py, s, d) in enumerate([(960, 350, 0.42, 0), (1120, 640, 0.45, 0), (730, 880, 0.44, 0), (1785, 250, 0.42, 0.5), (1665, 760, 0.45, -0.6),
                                     (1240, 1060, 0.6, -1.0), (1520, 1085, 0.65, -1.2), (360, 300, 0.32, 1.5)]):
    cloud(at(px, py, d), s, seed=i)

for i in range(22):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=random.uniform(0.01, 0.022), location=at(random.uniform(1150, 1900), random.uniform(250, 1050), random.uniform(-1.5, 0.5)))
    bpy.context.object.data.materials.append(SPARK)

# ---------------- world, lights, camera ----------------
world = bpy.data.worlds.new("w"); sc.world = world; world.use_nodes = True
wn = world.node_tree.nodes; wl = world.node_tree.links
bg_cam = wn["Background"]; bg_cam.inputs[0].default_value = (*BG, 1); bg_cam.inputs[1].default_value = 1.0
bg_lit = wn.new("ShaderNodeBackground"); bg_lit.inputs[0].default_value = (0.78, 0.76, 0.97, 1); bg_lit.inputs[1].default_value = 0.55
lp = wn.new("ShaderNodeLightPath"); mix = wn.new("ShaderNodeMixShader")
wl.new(lp.outputs["Is Camera Ray"], mix.inputs[0]); wl.new(bg_lit.outputs[0], mix.inputs[1]); wl.new(bg_cam.outputs[0], mix.inputs[2])
wl.new(mix.outputs[0], wn["World Output"].inputs[0])

def area(loc, rot, size, energy, color=(1, 1, 1)):
    bpy.ops.object.light_add(type="AREA", location=loc, rotation=rot)
    l = bpy.context.object; l.data.size = size; l.data.energy = energy; l.data.color = color
    return l
area((-7, -8, 7), (math.radians(55), 0, math.radians(-40)), 9, 680)
area((7, -6, 1), (math.radians(80), 0, math.radians(50)), 7, 260, (0.82, 0.78, 1.0))
area((0, -5, -9), (math.radians(160), 0, 0), 10, 380, (0.55, 0.45, 1.0))

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
