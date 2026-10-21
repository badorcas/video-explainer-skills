# Creative devices: when and how

Read this when the storyboard has a beat that 2D line art explains poorly. Everything here costs render time, tooling, or visual consistency, so each device has to earn its place.

## Contents
1. The budget and the test
2. Device catalog (what each is for, how to build it)
3. Asset sourcing and licensing
4. Keeping the style coherent

## 1. The budget and the test

- **Budget:** 1 to 3 signature moments per 10 minutes of video. Everything else is the restrained 2D house style.
- **Test before using a device:** would the explanation be weaker without it? "It looks cool" is not a reason. "The viewer can't see the third bounce in a 2D cross-section" is.
- **Placement:** the opening hook, the single hardest concept, and optionally the payoff. Never in the middle of a geometry derivation, where it would distract from the measurements.

## 2. Device catalog

### Morph between representations
For an idea that has two forms: a chirp graph becoming its spectrum, a time signal folding into its Fourier peaks, a ray diagram collapsing into an equation.
- Build: `ReplacementTransform`, or `TransformMatchingShapes` / `TransformMatchingTex` when the two forms share parts.
- Cheap, stays in the house style. This is the first creative tool to reach for.

### Camera moves in 2D
For a sense of scale, or for following an object.
- Build: `MovingCameraScene`. Zoom from a road overview into the van's rear bumper. Pan with the beam along its zigzag.
- Keep moves slow (2 to 4 s) and motivated by the narration.

### 3D geometry in manim
For an idea that is genuinely three-dimensional: corner reflectors, antenna patterns, wavefronts, rotations.
- Build: `ThreeDScene`. Use `Polygon` plates with `set_fill(opacity=0.25)`, a `VMobject` ray path, and `self.move_camera(phi=..., theta=...)` or `begin_ambient_camera_rotation(rate=0.1)`.
- Cairo handles a few dozen faces fine. Avoid dense surfaces.
- Return to an orthographic 2D view for anything with angles or lengths the viewer must read.

### 3D rendered objects (Blender)
For hero objects that need recognition, or a point-of-view shot. Example: "the van fills your windshield" shown from the driver's seat.
- Model: Kenney Car Kit (CC0, low-poly, consistent across vehicles), or Poly Haven (CC0).
- Render headless: `nix develop .#blender -c blender -b -P render.py`.
- Two looks that match the house style:
  - **Freestyle line art** exported as SVG (enable the Freestyle SVG Exporter add-on). Import with `SVGMobject`, recolor to INK, set strokes to about 2 px.
  - **Flat shading** in the palette (emission shader, 2 to 3 tones), transparent PNG sequence, imported with `ImageMobject`, one frame per manim frame.
- Use orthographic Blender cameras for top-down shots so they line up with the 2D geometry scenes. Perspective only for point-of-view shots.
- Moving parts (brake lights, signals, beams) stay as manim overlays anchored to the render's bounding box.

### Animated Blender objects (state library)
Use this when a realistic object must move: a spacecraft slewing, a boom ringing, an arm swinging. Rendering one Blender frame per video frame costs about 10 s a frame at 1080p, which is far too slow. Instead:
- **Look.** Use flat shading with a sun light, palette-coloured materials and real parts (bus, arrays with yokes, boom truss, star trackers, imager, antenna, thrusters). Add a gray Earth disk if the scene needs context. This read as "realistic" where icons did not.
- **State library.** Render a small set of states into a gitignored folder:
  - about 25 bend levels across [-max, max] for a vibration mode, with the bus counter-rotation baked in;
  - about 40 yaw steps for a slew.
  - Make the bend amplitude large: ±0.12 of the boom length read as nearly rigid, and ±0.26 (played back capped at ±0.18) read clearly.
  - Render a free-free mode for a free-flying craft: it crosses zero at a node and the bus moves opposite the tip. A clamped-root shape is wrong physics.
- **Playback.** Drive the state from a manim `ValueTracker` and an updater that picks the nearest library frame each manim frame. Keep one `ImageMobject` and swap its `pixel_array`; swapping child mobjects leaves a double craft. Never use `set_opacity` on transparent PNGs, because it turns them into opaque boxes.
- **Anchors.** Export the 2D screen positions of key parts per state as JSON (tip, root, imager, tracker, node). Overlays then attach to the right part in every frame.
- **Updaters.** They freeze during `self.wait()` unless the scene keeps them alive. Wait with a `keep_alive()` helper that plays an empty animation, or animate the tracker across the wait.

### Icon sets
The default for any recognizable object (planes, vehicles, people, servers, documents, sensors, buildings). Never hand-plot a polygon for one.
- Bundled: `assets/icons/` holds the Phosphor *fill* set (MIT). Load with `icon(name, h)` from style.py: off-white outline, opaque dark fill, which matches the house stroke style.
- More from the same family: `https://cdn.jsdelivr.net/npm/@phosphor-icons/core@2.1.1/assets/fill/<name>-fill.svg`. Other sources: Tabler, Lucide (MIT), game-icons.net (CC BY, needs attribution). Tabler SVGs include an invisible `M0 0h24v24H0z` bounding path that manim renders as a square; remove it.
- Import with `SVGMobject`. Use one family per video.
- Check at the real on-screen size, often 80 to 120 px at 1080p. Discard icons that turn to mush.

### Raster to vector
For a specific illustrated style that no icon set has.
- Source or generate the image outside the container, then vectorize with `vtracer` or `potrace` into SVG.
- Verify the license of the source image.

### Anatomy and biology
For eyes, brains, hearts, cells, and pathways between them. Freehand manim primitives (circles, bezier blobs) look amateurish here and distract the viewer.
- Start from an accurate vector source, never an improvised outline:
  - Servier Medical Art (smart.servier.com, CC BY 4.0, needs credit): organs, cells, sections; SVG/PPT.
  - Wikimedia Commons anatomical SVGs (check each file's license; many are CC BY-SA or public domain), e.g. sagittal brain, eye cross-section, visual pathway diagrams.
  - Gray's Anatomy plates (public domain) traced with `potrace`/`vtracer` when no SVG exists.
  - BioIcons (bioicons.com, mostly CC0/CC BY) for cells and lab objects.
- Simplify after import: drop shading and fills, keep the outline and only the internal structures the narration uses, recolor to INK at the house stroke weight. Keep proportions and positions; don't rescale parts independently.
- Use the textbook view for the concept: sagittal for cortex lobes, axial (inferior) view for the visual pathway (retina, optic nerve, chiasm, optic tract, LGN, optic radiations, V1), cross-section for the eye.
- Label every structure the narration names, with a thin leader line and the standard term, appearing as it is named. Move signals (a pulse along the pathway) as manim overlays on top of the imported outline.
- Check the frame against the reference image before rendering at high quality. Wrong anatomy (pathway through the wrong structure, cerebellum in the wrong place) is worse than no picture.

### Small multiples
For comparing conditions: with and without the reflector, at 1 to 4 m, in rain or clear.
- A grid of identical miniature plots sharing axes (Tufte). Often more creative and clearer than any animation.

## 3. Asset sourcing and licensing
- Prefer CC0 or MIT assets.
- CC BY requires an on-screen or description credit. Record it in the final summary.
- Never use branded or copyrighted characters, logos, or vehicle designs that identify a real make and model.

## 4. Keeping the style coherent
- Same palette, same stroke weight (2 px), same font across 2D, 3D and imported assets.
- A 3D shot should look like the same artist drew it: line art or flat palette shading, never photoreal next to Tufte plots.
- Cut, don't crossfade, between a 3D shot and a 2D scene, at a narration boundary.
- After rendering, view one contact sheet containing frames from both a 3D shot and a 2D scene together. If they look like two different videos, restyle the 3D.
