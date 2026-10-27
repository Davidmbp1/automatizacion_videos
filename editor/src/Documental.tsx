import React from "react";
import {
  AbsoluteFill,
  Audio,
  Img,
  OffthreadVideo,
  Sequence,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { TEXTO, TITULAR } from "./fuentes";
import type { Escena, Palabra, Props } from "./tipos";


const TRANSICION = 9; // frames de fundido entre escenas
const ES_VIDEO = (ruta: string) => ruta.toLowerCase().endsWith(".mp4");

const useEscala = () => {
  const { width, height } = useVideoConfig();
  return { s: Math.min(width, height) / 1080, vertical: height > width };
};

// ---------- Fondo: video o foto con movimiento de cámara y gradación de color ----------

const GRADO: React.CSSProperties = { filter: "contrast(1.08) saturate(0.88) brightness(0.93)" };

const Fondo: React.FC<{ escena: Escena; indice: number; atenuar?: boolean }> = ({ escena, indice, atenuar }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const t = frame / Math.max(1, durationInFrames);
  // alterna acercamiento, alejamiento y paneo para que ninguna escena se sienta estática
  const modo = indice % 3;
  const escala = modo === 1 ? 1.14 - 0.1 * t : 1.04 + 0.1 * t;
  const x = modo === 2 ? interpolate(t, [0, 1], [-2.5, 2.5]) : 0;
  const mov: React.CSSProperties = { transform: `scale(${escala}) translateX(${x}%)` };
  const filtroExtra = atenuar ? " blur(5px) brightness(0.42)" : "";
  const cubrir: React.CSSProperties = { width: "100%", height: "100%", objectFit: "cover" };

  if (ES_VIDEO(escena.fondo)) {
    return (
      <AbsoluteFill style={{ ...mov }}>
        <OffthreadVideo src={staticFile(escena.fondo)} muted style={{ ...cubrir, filter: GRADO.filter + filtroExtra }} />
      </AbsoluteFill>
    );
  }
  if (escena.tipo === "foto" && !atenuar) {
    // foto de archivo: fondo desenfocado + foto completa enmarcada, como en los documentales
    return (
      <AbsoluteFill>
        <Img src={staticFile(escena.fondo)} style={{ ...cubrir, filter: "blur(28px) brightness(0.45) saturate(0.8)", transform: "scale(1.2)" }} />
        <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", ...mov }}>
          <Img
            src={staticFile(escena.fondo)}
            style={{
              maxWidth: "84%",
              maxHeight: "80%",
              objectFit: "contain",
              boxShadow: "0 30px 80px rgba(0,0,0,0.7)",
              border: "6px solid rgba(255,255,255,0.92)",
              ...GRADO,
            }}
          />
        </AbsoluteFill>
      </AbsoluteFill>
    );
  }
  return (
    <AbsoluteFill style={{ ...mov }}>
      <Img src={staticFile(escena.fondo)} style={{ ...cubrir, filter: GRADO.filter + filtroExtra }} />
    </AbsoluteFill>
  );
};

// ---------- Tarjetas ----------

const Titulo: React.FC<{ escena: Escena; acento: string }> = ({ escena, acento }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { s } = useEscala();
  const entrada = spring({ frame, fps, config: { damping: 200 }, durationInFrames: 22 });
  const barra = spring({ frame: frame - 8, fps, config: { damping: 200 }, durationInFrames: 20 });
  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", padding: 90 * s }}>
      {escena.subtexto ? (
        <div style={{ fontFamily: TEXTO, fontWeight: 700, color: acento, letterSpacing: 10 * s, fontSize: 34 * s, opacity: entrada, marginBottom: 18 * s, textTransform: "uppercase" }}>
          {escena.subtexto}
        </div>
      ) : null}
      <div
        style={{
          fontFamily: TITULAR,
          color: "white",
          fontSize: 150 * s,
          lineHeight: 1.02,
          textAlign: "center",
          textTransform: "uppercase",
          clipPath: `inset(0 ${100 - entrada * 100}% 0 0)`,
          textShadow: "0 8px 40px rgba(0,0,0,0.6)",
        }}
      >
        {escena.texto}
      </div>
      <div style={{ height: 10 * s, width: `${barra * 34}%`, background: acento, marginTop: 30 * s }} />
    </AbsoluteFill>
  );
};

const Dato: React.FC<{ escena: Escena; acento: string; idioma: string }> = ({ escena, acento, idioma }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { s } = useEscala();
  const texto = escena.texto ?? "";
  // cuenta animada: anima la primera cifra del texto y conserva el resto ("$45.000 millones")
  const m = texto.match(/^(\D*?)(\d[\d.,]*)(.*)$/);
  let mostrado = texto;
  const avance = spring({ frame, fps, config: { damping: 200 }, durationInFrames: 40 });
  if (m) {
    const limpio = m[2].replace(/[.,](?=\d{3}\b)/g, "");
    const valor = parseFloat(limpio.replace(",", "."));
    if (!isNaN(valor)) {
      const decimales = (limpio.split(/[.,]/)[1] ?? "").length;
      const actual = (valor * avance).toFixed(decimales);
      const conMiles = Number(actual).toLocaleString(idioma === "es" ? "es-ES" : "en-US", { minimumFractionDigits: decimales, maximumFractionDigits: decimales });
      mostrado = `${m[1]}${conMiles}${m[3]}`;
    }
  }
  const pop = spring({ frame, fps, config: { damping: 12, mass: 0.6 } });
  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", padding: 80 * s }}>
      <div style={{ fontFamily: TITULAR, color: acento, fontSize: 210 * s, lineHeight: 1, transform: `scale(${0.7 + 0.3 * pop})`, textShadow: "0 10px 50px rgba(0,0,0,0.7)", textAlign: "center" }}>
        {mostrado}
      </div>
      {escena.subtexto ? (
        <div style={{ fontFamily: TEXTO, fontWeight: 700, color: "white", fontSize: 54 * s, marginTop: 24 * s, textAlign: "center", maxWidth: "80%", opacity: interpolate(frame, [10, 25], [0, 1], { extrapolateRight: "clamp" }) }}>
          {escena.subtexto}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};

const Cita: React.FC<{ escena: Escena; acento: string }> = ({ escena, acento }) => {
  const frame = useCurrentFrame();
  const { s } = useEscala();
  const palabras = (escena.texto ?? "").split(" ");
  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", padding: `0 ${140 * s}px` }}>
      <div style={{ fontFamily: TITULAR, color: acento, fontSize: 220 * s, lineHeight: 0.6, alignSelf: "flex-start", opacity: interpolate(frame, [0, 10], [0, 1], { extrapolateRight: "clamp" }) }}>“</div>
      <div style={{ fontFamily: TEXTO, fontWeight: 700, fontStyle: "italic", color: "white", fontSize: 64 * s, lineHeight: 1.3, textAlign: "center" }}>
        {palabras.map((p, i) => (
          <span key={i} style={{ opacity: interpolate(frame, [4 + i * 2.5, 12 + i * 2.5], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) }}>
            {p}{" "}
          </span>
        ))}
      </div>
      {escena.subtexto ? (
        <div style={{ fontFamily: TEXTO, fontWeight: 500, color: "#d8d8d8", fontSize: 38 * s, marginTop: 34 * s, letterSpacing: 2 * s }}>— {escena.subtexto}</div>
      ) : null}
    </AbsoluteFill>
  );
};

// ---------- Rótulo de lugar/fecha y crédito ----------

const Etiqueta: React.FC<{ texto: string; acento: string }> = ({ texto, acento }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const { s, vertical } = useEscala();
  const letras = Math.floor(interpolate(frame, [8, 8 + texto.length * 1.2], [0, texto.length], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }));
  const salida = interpolate(frame, [durationInFrames - 10, durationInFrames], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <div style={{ position: "absolute", left: 80 * s, top: vertical ? 260 * s : undefined, bottom: vertical ? undefined : 90 * s, display: "flex", alignItems: "center", gap: 18 * s, opacity: salida }}>
      <div style={{ width: 8 * s, height: 52 * s, background: acento }} />
      <div style={{ fontFamily: TEXTO, fontWeight: 900, color: "white", fontSize: 36 * s, letterSpacing: 6 * s, textTransform: "uppercase", textShadow: "0 2px 12px rgba(0,0,0,0.9)" }}>
        {texto.slice(0, letras)}
      </div>
    </div>
  );
};

const Credito: React.FC<{ texto: string }> = ({ texto }) => {
  const { s } = useEscala();
  return (
    <div style={{ position: "absolute", right: 30 * s, top: 24 * s, fontFamily: TEXTO, fontWeight: 500, fontSize: 18 * s, color: "rgba(255,255,255,0.75)", textShadow: "0 1px 4px black" }}>{texto}</div>
  );
};

// ---------- Subtítulos sincronizados palabra por palabra ----------

type Bloque = { palabras: Palabra[]; inicio: number; fin: number };

const agrupar = (palabras: Palabra[], max: number): Bloque[] => {
  const bloques: Bloque[] = [];
  let actual: Palabra[] = [];
  palabras.forEach((p, i) => {
    actual.push(p);
    const sig = palabras[i + 1];
    const corte = actual.length >= max || /[.,!?;:]$/.test(p.texto) || !sig || sig.inicio - p.fin > 0.35;
    if (corte) {
      bloques.push({ palabras: actual, inicio: actual[0].inicio, fin: p.fin });
      actual = [];
    }
  });
  // mantener cada bloque en pantalla hasta que empiece el siguiente (máx. 0.5 s extra)
  return bloques.map((b, i) => ({ ...b, fin: Math.min(bloques[i + 1]?.inicio ?? b.fin + 0.5, b.fin + 0.5) }));
};

const Subtitulos: React.FC<{ palabras: Palabra[]; ocultos: [number, number][]; acento: string }> = ({ palabras, ocultos, acento }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { s, vertical } = useEscala();
  const t = frame / fps;
  const bloques = React.useMemo(() => agrupar(palabras, vertical ? 3 : 5), [palabras, vertical]);
  if (ocultos.some(([a, b]) => t >= a && t < b)) return null;
  const bloque = bloques.find((b) => t >= b.inicio && t < b.fin);
  if (!bloque) return null;
  const pop = spring({ frame: frame - Math.round(bloque.inicio * fps), fps, config: { damping: 14, mass: 0.5 }, durationInFrames: 10 });
  return (
    <AbsoluteFill style={{ justifyContent: vertical ? "center" : "flex-end", alignItems: "center", paddingBottom: vertical ? 0 : 110 * s, paddingTop: vertical ? 520 * s : 0 }}>
      <div style={{ fontFamily: TEXTO, fontWeight: 900, fontSize: (vertical ? 86 : 66) * s, textAlign: "center", maxWidth: "86%", lineHeight: 1.15, transform: `scale(${0.88 + 0.12 * pop})`, textTransform: vertical ? "uppercase" : "none" }}>
        {bloque.palabras.map((p, i) => {
          const hablando = t >= p.inicio && t < p.fin + 0.05;
          return (
            <span
              key={i}
              style={{
                color: hablando ? acento : "white",
                textShadow: "0 0 3px black, 0 0 3px black, 0 4px 14px rgba(0,0,0,0.85)",
                WebkitTextStroke: `${3 * s}px black`,
                paintOrder: "stroke fill",
              }}
            >
              {p.texto}{" "}
            </span>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

// ---------- Capas de acabado: grano de película y viñeta ----------

const Acabado: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <AbsoluteFill style={{ background: "radial-gradient(ellipse at center, rgba(0,0,0,0) 55%, rgba(0,0,0,0.55) 100%)" }} />
      <AbsoluteFill
        style={{
          opacity: 0.08,
          mixBlendMode: "overlay",
          backgroundImage: `url(${staticFile("sfx/grano.png")})`,
          backgroundPosition: `${(frame * 137) % 512}px ${(frame * 263) % 512}px`,
        }}
      />
    </AbsoluteFill>
  );
};

// ---------- Composición principal ----------

const EscenaCompleta: React.FC<{ escena: Escena; indice: number; acento: string; fundido: boolean; idioma: string }> = ({ escena, indice, acento, fundido, idioma }) => {
  const frame = useCurrentFrame();
  const tarjeta = escena.tipo === "titulo" || escena.tipo === "dato" || escena.tipo === "cita";
  const opacidad = fundido ? interpolate(frame, [0, TRANSICION], [0, 1], { extrapolateRight: "clamp" }) : 1;
  return (
    <AbsoluteFill style={{ opacity: opacidad, backgroundColor: "black" }}>
      <Fondo escena={escena} indice={indice} atenuar={tarjeta} />
      {escena.tipo === "titulo" ? <Titulo escena={escena} acento={acento} /> : null}
      {escena.tipo === "dato" ? <Dato escena={escena} acento={acento} idioma={idioma} /> : null}
      {escena.tipo === "cita" ? <Cita escena={escena} acento={acento} /> : null}
      {escena.etiqueta && !tarjeta ? <Etiqueta texto={escena.etiqueta} acento={acento} /> : null}
      {escena.credito ? <Credito texto={escena.credito} /> : null}
      {tarjeta ? <Audio src={staticFile("sfx/whoosh.wav")} volume={0.35} /> : null}
    </AbsoluteFill>
  );
};

export const Documental: React.FC<Props> = (props) => {
  const { fps, durationInFrames } = useVideoConfig();
  const ocultos: [number, number][] = props.escenas
    .filter((e) => e.tipo !== "broll" && e.tipo !== "foto")
    .map((e) => [e.inicio, e.inicio + e.duracion]);

  return (
    <AbsoluteFill style={{ backgroundColor: "black" }}>
      {props.escenas.map((e, i) => {
        const desde = Math.round(e.inicio * fps);
        const solape = i === 0 ? 0 : TRANSICION;
        const largo = Math.max(1, Math.round(e.duracion * fps) + solape);
        return (
          <Sequence key={i} from={desde - solape} durationInFrames={largo} layout="none">
            <EscenaCompleta escena={e} indice={i} acento={props.colorAcento} fundido={i > 0} idioma={props.idioma ?? "en"} />
          </Sequence>
        );
      })}
      <Acabado />
      {props.subtitulos ? <Subtitulos palabras={props.palabras} ocultos={ocultos} acento={props.colorAcento} /> : null}
      {props.narracion ? <Audio src={staticFile(props.narracion)} /> : null}
      {props.musica ? (
        <Audio
          src={staticFile(props.musica)}
          loop
          volume={(f) => props.volumenMusica * interpolate(f, [0, fps, durationInFrames - 3 * fps, durationInFrames], [0, 1, 1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })}
        />
      ) : null}
    </AbsoluteFill>
  );
};
