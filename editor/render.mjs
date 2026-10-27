// Uso: node render.mjs <Documental|Miniatura> props.json salida.(mp4|jpg)
import { bundle } from "@remotion/bundler";
import { renderMedia, renderStill, selectComposition } from "@remotion/renderer";
import { readFileSync } from "node:fs";
import path from "node:path";
import os from "node:os";

const [, , id, archivoProps, salida] = process.argv;
const inputProps = JSON.parse(readFileSync(archivoProps, "utf-8"));
const browserExecutable = process.env.REMOTION_CHROME || null;

const serveUrl = await bundle({ entryPoint: path.resolve("src/index.ts"), publicDir: path.resolve("public") });
const composition = await selectComposition({ serveUrl, id, inputProps, browserExecutable });

if (id === "Miniatura") {
  await renderStill({ composition, serveUrl, output: salida, inputProps, browserExecutable, imageFormat: "jpeg", jpegQuality: 92 });
} else {
  let ultimo = -1;
  await renderMedia({
    composition,
    serveUrl,
    codec: "h264",
    crf: 23,
    audioBitrate: "192k",
    outputLocation: salida,
    inputProps,
    browserExecutable,
    concurrency: Math.max(1, os.cpus().length),
    onProgress: ({ progress }) => {
      const pct = Math.floor(progress * 100);
      if (pct >= ultimo + 10) {
        ultimo = pct;
        console.log(`  render ${pct}%`);
      }
    },
  });
}
console.log("  listo:", salida);
