# Crawl and Discovery Plugin Family

The crawl/discovery plugins overlap because they are all Katana-backed URL discovery workflows. Their catalog descriptions are intentionally distinct so users can choose the correct crawl mode.

| Plugin        | Engine   | Main purpose                     | Key execution difference                                     | Recommended use                                                         |
| ------------- | -------- | -------------------------------- | ------------------------------------------------------------ | ----------------------------------------------------------------------- |
| `katana`      | `katana` | Baseline URL and route discovery | Runs Katana with minimal flags: `katana -u {target} -silent` | Use for lightweight discovery when defaults are enough.                 |
| `crawler`     | `katana` | Recursive link discovery         | Adds configurable depth: `-depth {depth:2}`                  | Use when controlled recursive crawling is needed.                       |
| `spider`      | `katana` | JavaScript-aware crawling        | Adds JavaScript crawling and depth: `-jc -depth {depth:3}`   | Use for modern apps where client-side routes may expose more URLs.      |
| `sitemap_gen` | `katana` | Sitemap-style URL inventory      | Uses a deeper default crawl: `-depth {depth:4}`              | Use when the goal is a broader URL inventory rather than a quick crawl. |

## Boundary Notes

* These plugins were not renamed or merged in this change.
* All four plugins remain separate because they expose different crawl defaults or flags.
* `sitemap_gen` does not generate XML output. It produces discovered URL results suitable for sitemap-style inventory.
* `katana` is the baseline wrapper.
* `crawler` is the depth-controlled recursive crawler.
* `spider` is the JavaScript-aware crawler.
* `sitemap_gen` is the deeper inventory-oriented crawl.
