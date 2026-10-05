# Design decisions

Read [workflow](../../../../docs/workflow.md) and [format](../../../../docs/layout-format.md) first. The [visual review guide](../../../../docs/design-review.md) and [Hi example](../../../../examples/th3-hi/README.md) illustrate inspection and a composition, not a required font.

Choose case for whole-village readability. Uppercase often gives a stronger silhouette; title case can retain personal character. Preserve intended spelling rather than normalizing it silently. For a short name, reserve more breathing room instead of spending every wall on letter thickness.

Design on the integer grid while inspecting the isometric projection. Horizontal screen strokes follow increasing x and decreasing y; screen-vertical strokes increase both. This is design guidance, not an automatic font mapping. Author specific wall coordinates, adjust counters and spacing, then account for every remaining wall with deliberate framing or ornament.

Buildings should frame the lettering. Empty letter counters are useful grass, not available packing space. Surrounding traps count toward inventory too. Distinct schematic wall colors must not imply real differences when all walls are at the same level. Inspect a view with all wall colors equal before recommending a design.

Create the profile from [actual account input](../../../../docs/accounts.md) before design. Max templates require an explicit assumption and may not match a lower account's builders or levels. Retain exact completeness checks. If the word needs more walls than the account owns, simplify it or propose a shorter spelling. Never increase inventory beyond game caps.

For delivery, record which full-village views you inspected and your recommendation. Open the static HTML in a browser; exporting an image without inspecting it is insufficient. Do not claim attack performance or screenshot matching from a footprint schematic.
