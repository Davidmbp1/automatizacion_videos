import React from "react";
import { Composition, Still } from "remotion";
import { Documental } from "./Documental";
import { Miniatura } from "./Miniatura";
import type { Props } from "./tipos";

const ejemplo: Props = {
  ancho: 1920,
  alto: 1080,
  fps: 30,
  duracion: 5,
  narracion: "",
  volumenMusica: 0.1,
  escenas: [],
  palabras: [],
  colorAcento: "#FFD400",
  subtitulos: true,
};

export const Root: React.FC = () => (
  <>
  <Still
    id="Miniatura"
    component={Miniatura}
    width={1280}
    height={720}
    defaultProps={{ imagen: "", texto: "TITULO *AQUI*", acento: "#FFD400" }}
  />
  <Composition
    id="Documental"
    component={Documental}
    defaultProps={ejemplo}
    fps={30}
    width={1920}
    height={1080}
    durationInFrames={150}
    calculateMetadata={({ props }) => ({
      fps: props.fps,
      width: props.ancho,
      height: props.alto,
      durationInFrames: Math.max(1, Math.ceil(props.duracion * props.fps)),
    })}
  />
  </>
);
