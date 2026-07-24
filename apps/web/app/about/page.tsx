export default function AboutPage() {
  return (
    <>
      <h1>About LAoN</h1>
      <p className="lead">
        Lost Ancient Arts of Nepal is an independent open-source project. It
        helps people browse documented objects and find possible visual matches
        against open museum images and a curated catalog.
      </p>

      <div className="panel">
        <strong>Core disclaimer</strong>
        <p style={{ margin: "0.5rem 0 0" }}>
          Possible visual match — not a determination of legal ownership. LAoN
          does not file restitution claims. Only authorized government channels
          can pursue formal legal action.
        </p>
      </div>

      <h2>What you can do</h2>
      <ul>
        <li>
          <strong>Visitor camera</strong> at <code>/visit</code> — take a photo
          in a gallery or temple on your phone (installable PWA)
        </li>
        <li>Browse catalog entries (status, place, iconography tags)</li>
        <li>Open original-site pins on a simple map list</li>
        <li>Upload a photo for ranked possible matches</li>
        <li>Download a JSON evidence package to share with experts you trust</li>
      </ul>

      <h2>Is there a mobile app?</h2>
      <p>
        Yes in practice: the <strong>Progressive Web App</strong> visitor camera.
        Open the site on your phone, use <code>/visit</code>, then{" "}
        <em>Add to Home Screen</em>. No App Store fees for a social project. A
        native store app can wrap the same flow later if needed.
      </p>

      <h2>Dual corpus</h2>
      <p>
        The public git repository ships only rights-cleared images (e.g. Met and
        Cleveland CC0) plus metadata and bibliographic citations. Operators may
        attach a private research corpus (book plates you photographed) via{" "}
        <code>PRIVATE_CORPUS_PATH</code> to improve matching on their own
        machines. Private images are never committed.
      </p>

      <h2>Data sources we credit</h2>
      <ul>
        <li>Metropolitan Museum of Art Open Access / Collection API (CC0)</li>
        <li>Cleveland Museum of Art Open Access API (CC0)</li>
        <li>
          Scholarly documentation such as Bangdel, <em>Stolen Images of Nepal</em>{" "}
          (1989) — citation only unless you hold rights to images
        </li>
        <li>
          Huntington Archive lost/stolen Nepal pages (link-out; respect their
          terms)
        </li>
        <li>
          Public reporting on repatriations (Met, Rubin, community cases)
        </li>
      </ul>
      <p className="meta">
        LAoN is not affiliated with NHRC, Lost Arts of Nepal, HAR, Global Nepali
        Museum, or any museum. We may cite their public work without implying
        partnership.
      </p>

      <h2>Ethics</h2>
      <p>
        See <code>docs/ethics.md</code> in the repository for soft language rules,
        licensing, and why there is no “send claim” button.
      </p>

      <h2>Open source</h2>
      <p>
        Code is MIT-licensed. Contributions welcome under the project Code of
        Conduct. Expand the seed catalog carefully — every public image needs a
        license and attribution.
      </p>
    </>
  );
}
