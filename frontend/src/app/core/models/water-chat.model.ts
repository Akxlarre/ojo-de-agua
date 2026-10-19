import { DiagnosticoCuenca, ResultadoProrrateo } from './water-domain.model';

export type ChatMessageRole = 'user' | 'assistant' | 'system';

export type DomainArtifactType =
  | 'cuenca_kpi'
  | 'apr_threat_alert'
  | 'prorrateo_simulator'
  | 'glaciar_summary'
  | 'legal_citation_card';

/** Cita legal formal que respalda la respuesta del copiloto */
export interface LegalCitation {
  id: string;
  norma: string; // Ej: "Ley 21.435" o "DFL 1.122"
  articulo: string; // Ej: "Art. 5 bis" o "Art. 314"
  descripcion: string;
  urlOficial?: string;
}

/** Paso de razonamiento o llamada a herramienta del agente (Chain of Thought) */
export interface ThoughtStep {
  id: string;
  pasoNumero: number;
  titulo: string;
  detalle?: string;
  tiempoEjecucionMs?: number;
  herramientaInvocada?: string;
}

/** Widget interactivo vivo (Generative UI) insertado en el flujo del chat */
export interface DomainArtifact {
  id: string;
  tipo: DomainArtifactType;
  titulo: string;
  subtitulo?: string;
  cuencaCodigo?: string;
  datosDiagnostico?: DiagnosticoCuenca;
  datosProrrateo?: ResultadoProrrateo;
  payloadExtra?: Record<string, unknown>;
}

/** Mensaje individual en la conversación */
export interface ChatMessage {
  id: string;
  role: ChatMessageRole;
  content: string;
  timestamp: Date;
  isStreaming?: boolean;
  thoughts?: ThoughtStep[];
  artifacts?: DomainArtifact[];
  citations?: LegalCitation[];
}

/** Hilo de conversación guardado */
export interface ChatThread {
  id: string;
  title: string;
  cuencaCodigo?: string;
  createdAt: Date;
  updatedAt: Date;
  totalMensajes: number;
}

/** Eventos que emite el endpoint Server-Sent Events (SSE) del copiloto AI */
export type StreamEventType =
  | 'thought'
  | 'chunk'
  | 'artifact'
  | 'citation'
  | 'done'
  | 'error';

export interface AgentStreamEvent {
  tipo: StreamEventType;
  contenido?: string;
  thought?: ThoughtStep;
  artifact?: DomainArtifact;
  citation?: LegalCitation;
  error?: string;
}
