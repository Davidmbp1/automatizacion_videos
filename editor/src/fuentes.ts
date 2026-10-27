// Fuentes incluidas en public/fuentes (licencia SIL OFL), así el render no depende de internet.
import { loadFont } from "@remotion/fonts";
import { staticFile } from "remotion";

export const TITULAR = "Anton";
export const TEXTO = "Inter";

loadFont({ family: TITULAR, url: staticFile("fuentes/anton.woff2"), weight: "400" });
loadFont({ family: TEXTO, url: staticFile("fuentes/inter.woff2"), weight: "100 900", style: "normal" });
loadFont({ family: TEXTO, url: staticFile("fuentes/inter-italic.woff2"), weight: "100 900", style: "italic" });
