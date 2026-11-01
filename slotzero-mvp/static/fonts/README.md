# Local font provenance

The app serves these two variable WOFF2 faces locally, with `font-display: swap` and matching preload declarations. No Google Fonts stylesheet or font request is needed at runtime.

| Shipped face | Upstream source | License |
|---|---|---|
| Lexend (`lexend-latin-variable.woff2`) | [Google Fonts Lexend variable TTF](https://github.com/google/fonts/blob/main/ofl/lexend/Lexend%5Bwght%5D.ttf) | SIL Open Font License 1.1; see LEXEND-OFL.txt |
| Source Sans 3 (`source-sans-3-variable.woff2`) | [Google Fonts Source Sans 3 variable TTF](https://github.com/google/fonts/blob/main/ofl/sourcesans3/SourceSans3%5Bwght%5D.ttf) | SIL Open Font License 1.1; see SOURCE-SANS-3-OFL.txt |

Downloaded for the 2026-11-01 redesign and losslessly converted from the official TTF files using the existing fontTools environment. Glyph order was preserved; this was container compression, not glyph subsetting. The Lexend filename's `latin` label is not a claim that its original glyph set was reduced. Combined shipped font size: 241,540 bytes.

Lexend is declared at weights 100–900 and Source Sans 3 at 200–900. The UI uses Lexend 500 for headings and primarily Source Sans 3 400/600 for content and controls. Keep the accompanying license notices with redistributions.
