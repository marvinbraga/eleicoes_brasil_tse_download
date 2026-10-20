"use client";

import { useEffect, useRef, useState, type CSSProperties } from "react";

const VERMELHO = "255,40,40";
const AMARELO = "255,230,0";
const SUMICO_MS = 3000;
const COMPRIMENTO_INICIAL = 50;
const LARGURA = 3;
const LARGURA_BRILHO = 14;
const SUAVIZAR = 0.35;
const ALFA_MARCA = 0.28;
const ALFA_BORDA = 0.5;

type Ponto = { x: number; y: number };
type PontoTempo = Ponto & { t: number };
type Trilha = {
  ancora: HTMLElement;
  pontos: PontoTempo[];
  fechada: boolean;
  fechadaEm: number | null;
};
type Retangulo = { ancora: HTMLElement; x: number; y: number; w: number; h: number };
type Recorte = { x: number; y: number; w: number; h: number };

type Sessao = {
  laser: boolean;
  marca: boolean;
  desenhando: boolean;
  arrastando: boolean;
  trilhas: Trilha[];
  trilha: Trilha | null;
  retangulos: Retangulo[];
  inicio: Ponto | null;
  atual: Ponto | null;
  ancoraArraste: HTMLElement | null;
  quadro: number | null;
};

export function FerramentasApresentacao() {
  const raiz = useRef<HTMLParagraphElement>(null);
  const laserRef = useRef<HTMLCanvasElement>(null);
  const marcaRef = useRef<HTMLCanvasElement>(null);
  const sessao = useRef<Sessao>(sessaoVazia());
  const [aviso, setAviso] = useState("");

  useEffect(() => {
    const laser = laserRef.current;
    const marca = marcaRef.current;
    const estado = sessao.current;
    if (!laser || !marca) {
      return;
    }
    const contextoLaser = laser.getContext("2d");
    const contextoMarca = marca.getContext("2d");
    if (!contextoLaser || !contextoMarca) {
      return;
    }

    const paginaVista = () => paginaVisivel(raiz.current);

    const publicar = () => {
      const partes: string[] = [];
      if (estado.laser) {
        partes.push("Laser ligado");
      }
      if (estado.marca) {
        partes.push("Marca-texto ligado");
      }
      const ligado = (estado.laser || estado.marca) && paginaVista();
      document.body.style.cursor = ligado ? "crosshair" : "";
      document.body.style.userSelect = ligado ? "none" : "";
      setAviso(partes.join(". "));
    };

    const ajustar = () => {
      encaixar(laser, contextoLaser);
      encaixar(marca, contextoMarca);
      pintarMarcas(marca, contextoMarca, estado);
    };

    const aoTeclar = (evento: KeyboardEvent) => {
      if (!paginaVista()) {
        return;
      }
      if (evento.repeat || evento.ctrlKey || evento.metaKey || evento.altKey) {
        return;
      }
      if (ignoraTecla(evento.target)) {
        return;
      }
      if (evento.key === "k" || evento.key === "K") {
        estado.laser = !estado.laser;
        if (!estado.laser) {
          pararLaser(estado);
        }
        publicar();
      } else if (evento.key === "m" || evento.key === "M") {
        estado.marca = !estado.marca;
        if (!estado.marca) {
          limparMarcas(marca, contextoMarca, estado);
        }
        publicar();
      } else if (evento.key === "Escape") {
        estado.laser = false;
        pararLaser(estado);
        publicar();
      }
    };

    const ferramentaLigada = (evento: MouseEvent) =>
      evento.button === 0 && paginaVista() && (estado.laser || estado.marca);

    const segurarArraste = (evento: MouseEvent) => {
      if (!ferramentaLigada(evento)) {
        return;
      }
      evento.preventDefault();
    };

    const bloquearClique = (evento: MouseEvent) => {
      if (!ferramentaLigada(evento)) {
        return;
      }
      evento.preventDefault();
      evento.stopPropagation();
    };

    const aoPressionar = (evento: MouseEvent) => {
      if (evento.button !== 0 || !paginaVista()) {
        return;
      }
      const ancora = ancoraDe(evento.target);
      const ponto = pontoNoConteudo(evento, ancora);
      if (estado.laser) {
        comecarLaser(estado, ancora, ponto, laser, contextoLaser);
      }
      if (estado.marca) {
        estado.arrastando = true;
        estado.ancoraArraste = ancora;
        estado.inicio = ponto;
        estado.atual = ponto;
        pintarMarcas(marca, contextoMarca, estado);
      }
    };

    const aoMover = (evento: MouseEvent) => {
      if (!paginaVista()) {
        return;
      }
      if (estado.desenhando && estado.trilha) {
        moverLaser(evento, estado);
      }
      if (estado.arrastando && estado.inicio && estado.ancoraArraste) {
        estado.atual = pontoNoConteudo(evento, estado.ancoraArraste);
        pintarMarcas(marca, contextoMarca, estado);
      }
    };

    const aoSoltar = (evento: MouseEvent) => {
      if (evento.button !== 0 || !paginaVista()) {
        return;
      }
      if (estado.desenhando) {
        pararLaser(estado);
      }
      if (estado.arrastando) {
        concluirMarca(marca, contextoMarca, estado);
      }
    };

    const aoSair = () => {
      if (estado.desenhando) {
        pararLaser(estado);
      }
      if (estado.arrastando) {
        concluirMarca(marca, contextoMarca, estado);
      }
    };

    const aoRolar = () => {
      pintarMarcas(marca, contextoMarca, estado);
    };

    const sincronizarPagina = () => {
      if (paginaVista()) {
        publicar();
        return;
      }
      if (estado.desenhando) {
        pararLaser(estado);
      }
      if (estado.arrastando) {
        concluirMarca(marca, contextoMarca, estado);
      }
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };

    const observador = new MutationObserver(sincronizarPagina);
    let ancestral: Node | null = raiz.current?.closest(".leitura") ?? raiz.current;
    while (ancestral && ancestral !== document.body) {
      if (ancestral instanceof HTMLElement) {
        observador.observe(ancestral, { attributes: true, attributeFilter: ["style", "hidden"] });
      }
      ancestral = ancestral.parentElement;
    }

    ajustar();
    sincronizarPagina();
    document.addEventListener("keydown", aoTeclar);
    document.addEventListener("mousedown", segurarArraste, true);
    document.addEventListener("click", bloquearClique, true);
    document.addEventListener("mousedown", aoPressionar);
    document.addEventListener("mousemove", aoMover);
    document.addEventListener("mouseup", aoSoltar);
    document.addEventListener("mouseleave", aoSair);
    document.addEventListener("scroll", aoRolar, true);
    window.addEventListener("resize", ajustar);

    return () => {
      observador.disconnect();
      document.removeEventListener("keydown", aoTeclar);
      document.removeEventListener("mousedown", segurarArraste, true);
      document.removeEventListener("click", bloquearClique, true);
      document.removeEventListener("mousedown", aoPressionar);
      document.removeEventListener("mousemove", aoMover);
      document.removeEventListener("mouseup", aoSoltar);
      document.removeEventListener("mouseleave", aoSair);
      document.removeEventListener("scroll", aoRolar, true);
      window.removeEventListener("resize", ajustar);
      if (estado.quadro !== null) {
        cancelAnimationFrame(estado.quadro);
        estado.quadro = null;
      }
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };
  }, []);

  return (
    <>
      <p
        ref={raiz}
        className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-muted-foreground print:hidden"
      >
        <kbd className="rounded-sm border border-border px-1.5 font-sans text-foreground">K</kbd>
        laser
        <kbd className="rounded-sm border border-border px-1.5 font-sans text-foreground">M</kbd>
        marca-texto
        <kbd className="rounded-sm border border-border px-1.5 font-sans text-foreground">Esc</kbd>
        solta o laser
        <span aria-live="polite" className="text-foreground">
          {aviso}
        </span>
      </p>
      <canvas ref={laserRef} aria-hidden="true" style={estiloTela(99999)} className="print:hidden" />
      <canvas ref={marcaRef} aria-hidden="true" style={estiloTela(9997)} className="print:hidden" />
    </>
  );
}

function paginaVisivel(no: HTMLElement | null): boolean {
  return !!no && no.isConnected && no.getClientRects().length > 0;
}

function sessaoVazia(): Sessao {
  return {
    laser: false,
    marca: false,
    desenhando: false,
    arrastando: false,
    trilhas: [],
    trilha: null,
    retangulos: [],
    inicio: null,
    atual: null,
    ancoraArraste: null,
    quadro: null,
  };
}

function estiloTela(camada: number): CSSProperties {
  return {
    position: "fixed",
    inset: 0,
    width: "100%",
    height: "100%",
    pointerEvents: "none",
    zIndex: camada,
  };
}

function ignoraTecla(alvo: EventTarget | null): boolean {
  if (!(alvo instanceof HTMLElement)) {
    return false;
  }
  const etiqueta = alvo.tagName;
  if (etiqueta === "INPUT" || etiqueta === "TEXTAREA" || etiqueta === "SELECT") {
    return true;
  }
  return alvo.closest("[role='listbox'], [role='option']") !== null;
}

function ancoraDe(alvo: EventTarget | null): HTMLElement {
  let no = alvo instanceof Element ? alvo : null;
  while (no && no !== document.body) {
    if (no instanceof HTMLElement && (no.classList.contains("folha") || no.classList.contains("leitura"))) {
      return no;
    }
    no = no.parentElement;
  }
  return documento();
}

function documento(): HTMLElement {
  return document.scrollingElement instanceof HTMLElement
    ? document.scrollingElement
    : document.documentElement;
}

function ehPagina(ancora: HTMLElement): boolean {
  return ancora === document.body || ancora === document.documentElement || ancora === document.scrollingElement;
}

function pontoNoConteudo(evento: MouseEvent, ancora: HTMLElement): Ponto {
  if (ehPagina(ancora)) {
    return { x: evento.clientX + window.scrollX, y: evento.clientY + window.scrollY };
  }
  const caixa = ancora.getBoundingClientRect();
  return {
    x: evento.clientX - caixa.left + ancora.scrollLeft,
    y: evento.clientY - caixa.top + ancora.scrollTop,
  };
}

function paraVista(x: number, y: number, ancora: HTMLElement): Ponto {
  if (ehPagina(ancora)) {
    return { x: x - window.scrollX, y: y - window.scrollY };
  }
  const caixa = ancora.getBoundingClientRect();
  return { x: caixa.left + x - ancora.scrollLeft, y: caixa.top + y - ancora.scrollTop };
}

function recorteDe(ancora: HTMLElement): Recorte | null {
  if (ehPagina(ancora)) {
    return null;
  }
  const caixa = ancora.getBoundingClientRect();
  let topo = caixa.top;
  if (ancora.classList.contains("folha")) {
    const cabeca = ancora.querySelector("thead th");
    if (cabeca) {
      const cabecaCaixa = cabeca.getBoundingClientRect();
      if (cabecaCaixa.bottom > topo && cabecaCaixa.bottom < caixa.bottom) {
        topo = cabecaCaixa.bottom;
      }
    }
  }
  return { x: caixa.left, y: topo, w: caixa.width, h: Math.max(0, caixa.bottom - topo) };
}

function encaixar(tela: HTMLCanvasElement, contexto: CanvasRenderingContext2D) {
  const densidade = window.devicePixelRatio || 1;
  tela.width = Math.round(window.innerWidth * densidade);
  tela.height = Math.round(window.innerHeight * densidade);
  contexto.setTransform(densidade, 0, 0, densidade, 0, 0);
}

function comecarLaser(
  estado: Sessao,
  ancora: HTMLElement,
  ponto: Ponto,
  tela: HTMLCanvasElement,
  contexto: CanvasRenderingContext2D,
) {
  estado.desenhando = true;
  estado.trilha = {
    ancora,
    pontos: [{ x: ponto.x, y: ponto.y, t: performance.now() }],
    fechada: false,
    fechadaEm: null,
  };
  estado.trilhas.push(estado.trilha);
  if (estado.quadro === null) {
    quadroLaser(estado, tela, contexto);
  }
}

function moverLaser(evento: MouseEvent, estado: Sessao) {
  const trilha = estado.trilha;
  if (!trilha) {
    return;
  }
  const pontos = trilha.pontos;
  const ultimo = pontos[pontos.length - 1];
  if (!ultimo) {
    return;
  }
  const ponto = pontoNoConteudo(evento, trilha.ancora);
  const proximo = SUAVIZAR > 0 ? interpolar(ponto, ultimo, SUAVIZAR) : ponto;
  if (distancia(ultimo, proximo) > 2) {
    pontos.push({ x: proximo.x, y: proximo.y, t: performance.now() });
  }
}

function pararLaser(estado: Sessao) {
  if (estado.trilha && !estado.trilha.fechada) {
    estado.trilha.fechada = true;
    estado.trilha.fechadaEm = performance.now();
  }
  estado.desenhando = false;
  estado.trilha = null;
}

function quadroLaser(estado: Sessao, tela: HTMLCanvasElement, contexto: CanvasRenderingContext2D) {
  const agora = performance.now();
  contexto.clearRect(0, 0, tela.width / (window.devicePixelRatio || 1), tela.height / (window.devicePixelRatio || 1));
  contexto.shadowBlur = 0;
  estado.trilhas = estado.trilhas.filter((trilha) => desenharTrilha(trilha, agora, contexto) || !trilha.fechada);
  if (estado.trilhas.length > 0 || estado.desenhando) {
    estado.quadro = requestAnimationFrame(() => quadroLaser(estado, tela, contexto));
  } else {
    estado.quadro = null;
  }
}

function desenharTrilha(trilha: Trilha, agora: number, contexto: CanvasRenderingContext2D): boolean {
  const pontos = trilha.pontos;
  if (pontos.length < 2) {
    return false;
  }
  const comprimentos = comprimentosDa(pontos);
  let primeiro = -1;
  for (let indice = 0; indice < pontos.length; indice += 1) {
    const percorrido = comprimentos[indice] ?? 0;
    if (opacidade(percorrido, agora, trilha) > 0.005) {
      primeiro = indice;
      break;
    }
  }
  if (primeiro < 0) {
    return false;
  }
  let visivel = false;
  const recorte = recorteDe(trilha.ancora);
  contexto.save();
  if (recorte) {
    contexto.beginPath();
    contexto.rect(recorte.x, recorte.y, recorte.w, recorte.h);
    contexto.clip();
  }
  for (let indice = Math.max(1, primeiro); indice < pontos.length; indice += 1) {
    const alfa = opacidade(comprimentos[indice] ?? 0, agora, trilha);
    if (alfa < 0.005) {
      continue;
    }
    visivel = true;
    const anterior = pontos[indice - 1];
    const corrente = pontos[indice];
    if (!anterior || !corrente) {
      continue;
    }
    const de = paraVista(anterior.x, anterior.y, trilha.ancora);
    const para = paraVista(corrente.x, corrente.y, trilha.ancora);
    tracar(contexto, de, para, LARGURA_BRILHO * alfa, 16 * alfa, `rgba(${VERMELHO},${alfa * 0.35})`);
    contexto.beginPath();
    contexto.moveTo(de.x, de.y);
    contexto.lineTo(para.x, para.y);
    contexto.strokeStyle = `rgba(255,255,255,${alfa})`;
    contexto.lineWidth = LARGURA * alfa;
    contexto.shadowBlur = 6 * alfa;
    contexto.stroke();
  }
  contexto.restore();
  return visivel;
}

function tracar(
  contexto: CanvasRenderingContext2D,
  de: Ponto,
  para: Ponto,
  largura: number,
  brilho: number,
  tinta: string,
) {
  contexto.beginPath();
  contexto.moveTo(de.x, de.y);
  contexto.lineTo(para.x, para.y);
  contexto.lineWidth = largura;
  contexto.lineCap = "round";
  contexto.shadowBlur = brilho;
  contexto.strokeStyle = tinta;
  contexto.shadowColor = tinta;
  contexto.stroke();
}

function opacidade(percorrido: number, agora: number, trilha: Trilha): number {
  let alfa = 1;
  if (trilha.fechada && trilha.fechadaEm !== null) {
    alfa = saida(Math.max(0, 1 - (agora - trilha.fechadaEm) / SUMICO_MS));
  }
  if (percorrido < COMPRIMENTO_INICIAL) {
    alfa = Math.min(alfa, saida(percorrido / COMPRIMENTO_INICIAL));
  }
  return alfa;
}

function comprimentosDa(pontos: readonly Ponto[]): number[] {
  const comprimentos = [0];
  for (let indice = 1; indice < pontos.length; indice += 1) {
    const anterior = pontos[indice - 1];
    const corrente = pontos[indice];
    const ultimo = comprimentos[indice - 1] ?? 0;
    comprimentos.push(ultimo + (anterior && corrente ? distancia(anterior, corrente) : 0));
  }
  return comprimentos;
}

function pintarMarcas(tela: HTMLCanvasElement, contexto: CanvasRenderingContext2D, estado: Sessao) {
  contexto.clearRect(0, 0, tela.width / (window.devicePixelRatio || 1), tela.height / (window.devicePixelRatio || 1));
  for (const retangulo of estado.retangulos) {
    pintarRetangulo(contexto, retangulo);
  }
  if (estado.arrastando && estado.inicio && estado.atual && estado.ancoraArraste) {
    pintarRetangulo(contexto, caixa(estado.ancoraArraste, estado.inicio, estado.atual));
  }
}

function concluirMarca(tela: HTMLCanvasElement, contexto: CanvasRenderingContext2D, estado: Sessao) {
  if (estado.inicio && estado.atual && estado.ancoraArraste) {
    const retangulo = caixa(estado.ancoraArraste, estado.inicio, estado.atual);
    if (retangulo.w > 4 && retangulo.h > 4) {
      estado.retangulos.push(retangulo);
    }
  }
  estado.arrastando = false;
  estado.inicio = null;
  estado.atual = null;
  estado.ancoraArraste = null;
  pintarMarcas(tela, contexto, estado);
}

function limparMarcas(tela: HTMLCanvasElement, contexto: CanvasRenderingContext2D, estado: Sessao) {
  estado.retangulos = [];
  estado.arrastando = false;
  estado.inicio = null;
  estado.atual = null;
  estado.ancoraArraste = null;
  pintarMarcas(tela, contexto, estado);
}

function pintarRetangulo(contexto: CanvasRenderingContext2D, retangulo: Retangulo) {
  const origem = paraVista(retangulo.x, retangulo.y, retangulo.ancora);
  const recorte = recorteDe(retangulo.ancora);
  contexto.save();
  if (recorte) {
    contexto.beginPath();
    contexto.rect(recorte.x, recorte.y, recorte.w, recorte.h);
    contexto.clip();
  }
  const tinta = `rgba(${AMARELO},`;
  contexto.fillStyle = `${tinta}${ALFA_MARCA})`;
  contexto.fillRect(origem.x, origem.y, retangulo.w, retangulo.h);
  contexto.strokeStyle = `${tinta}${ALFA_BORDA})`;
  contexto.lineWidth = 1.5;
  contexto.strokeRect(origem.x, origem.y, retangulo.w, retangulo.h);
  contexto.restore();
}

function caixa(ancora: HTMLElement, inicio: Ponto, atual: Ponto): Retangulo {
  return {
    ancora,
    x: Math.min(inicio.x, atual.x),
    y: Math.min(inicio.y, atual.y),
    w: Math.abs(atual.x - inicio.x),
    h: Math.abs(atual.y - inicio.y),
  };
}

function saida(valor: number): number {
  return 1 - (1 - valor) ** 3;
}

function distancia(origem: Ponto, destino: Ponto): number {
  const dx = destino.x - origem.x;
  const dy = destino.y - origem.y;
  return Math.sqrt(dx * dx + dy * dy);
}

function interpolar(origem: Ponto, destino: Ponto, parte: number): Ponto {
  return {
    x: origem.x + (destino.x - origem.x) * parte,
    y: origem.y + (destino.y - origem.y) * parte,
  };
}
