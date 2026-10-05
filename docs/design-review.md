# Review lettering in the whole village

Inspect the static HTML in a browser after validation. The isometric view shows the intended village orientation; the overhead view exposes tile origins and gaps. Both derive from the same coordinates.

Use these questions to review the layout:

- Does the spelling and requested case read clearly at whole-village scale?
- Are letter gaps, spaces inside letters (counters) and dots distinct from framing walls?
- Do the strokes have a consistent thickness, with enough open grass around the name?
- Do surrounding buildings support the composition without competing with it?
- Would tall game sprites conceal strokes that the schematic leaves visible?

The [TH3 Hi example](../examples/th3-hi/README.md) uses a capital H and dotted lowercase i. Its reviewed schematics show separate strokes and a clear central word. This demonstrates visual assessment, not a universal style or font.

Record the inspected views, date and conclusion in `visual_review`, separate from Python diagnostics. A model pass cannot establish that lettering is attractive. If a view cannot be inspected, record that limitation; do not claim completed visual acceptance.

Schematics use labelled footprint shapes and uniform wall markers. They omit sprite heights, art and combat behavior. In-game acceptance remains unconfirmed until the editor accepts the constructed design.
