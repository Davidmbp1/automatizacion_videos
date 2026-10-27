import React from "react";
import { AbsoluteFill, Img, staticFile } from "remotion";
import { TEXTO, TITULAR } from "./fuentes";


export type PropsMiniatura = {
  imagen: string; // ruta en public/
  texto: string; // 2-4 palabras; la palabra entre *asteriscos* va resaltada
  etiqueta?: string; // texto pequeño arriba, p. ej. "$100,000 STOLEN"
  acento: string;
};

export const Miniatura: React.FC<PropsMiniatura> = ({ imagen, texto, etiqueta, acento }) => {
  const partes = texto.split(/(\*[^*]+\*)/).filter(Boolean);
  return (
    <AbsoluteFill style={{ backgroundColor: "#0a0a0a" }}>
      <Img
        src={staticFile(imagen)}
        style={{
          position: "absolute",
          right: 0,
          width: "72%",
          height: "100%",
          objectFit: "cover",
          filter: "contrast(1.25) saturate(1.2) brightness(1.02)",
        }}
      />
      {/* fundido oscuro hacia la izquierda para el texto */}
      <AbsoluteFill style={{ background: "linear-gradient(90deg, #0a0a0a 30%, rgba(10,10,10,0.85) 45%, rgba(10,10,10,0) 72%)" }} />
      <AbsoluteFill style={{ background: "radial-gradient(ellipse at 70% 50%, rgba(0,0,0,0) 40%, rgba(0,0,0,0.55) 100%)" }} />
      <AbsoluteFill style={{ justifyContent: "center", paddingLeft: 56, width: "60%" }}>
        {etiqueta ? (
          <div style={{ alignSelf: "flex-start", background: "#E50914", color: "white", fontFamily: TEXTO, fontWeight: 900, fontSize: 34, padding: "6px 16px", marginBottom: 18, transform: "rotate(-2deg)", textTransform: "uppercase" }}>
            {etiqueta}
          </div>
        ) : null}
        <div style={{ fontFamily: TITULAR, fontSize: 128, lineHeight: 1.12, color: "white", textTransform: "uppercase", textShadow: "0 6px 0 rgba(0,0,0,0.6), 0 12px 40px rgba(0,0,0,0.8)" }}>
          {partes.map((p, i) =>
            p.startsWith("*") ? (
              <span key={i} style={{ display: "inline-block", color: "#0a0a0a", background: acento, padding: "4px 14px 0", marginTop: 10, lineHeight: 1.0, textShadow: "none", transform: "rotate(-1.5deg)" }}>
                {p.slice(1, -1)}
              </span>
            ) : (
              <span key={i}>{p}</span>
            ),
          )}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
