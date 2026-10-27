export type TipoEscena = "broll" | "foto" | "titulo" | "dato" | "cita";

export type Escena = {
  tipo: TipoEscena;
  inicio: number; // segundos
  duracion: number; // segundos
  fondo: string; // ruta dentro de public/ (video .mp4 o imagen)
  texto?: string; // título, número, o cita
  subtexto?: string; // etiqueta del dato, autor de la cita
  credito?: string; // crédito de la foto (licencias CC)
  etiqueta?: string; // rótulo inferior tipo "JULIO 2020 · FLORIDA"
};

export type Palabra = { texto: string; inicio: number; fin: number };

export type Props = {
  ancho: number;
  alto: number;
  fps: number;
  duracion: number;
  narracion: string;
  musica?: string;
  volumenMusica: number;
  escenas: Escena[];
  palabras: Palabra[];
  colorAcento: string;
  subtitulos: boolean;
  idioma?: string;
};
