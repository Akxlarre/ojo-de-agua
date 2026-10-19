import { Injectable, computed, inject, signal } from '@angular/core';
import { WaterAiStreamService } from '@core/services/ai/water-ai-stream.service';
import {
  AgentStreamEvent,
  ChatMessage,
  ChatThread,
  DomainArtifact,
  ThoughtStep,
} from '@core/models/water-chat.model';

@Injectable({
  providedIn: 'root',
})
export class WaterChatFacade {
  private readonly streamService = inject(WaterAiStreamService);

  // --- Signals de Estado Central ---
  private readonly _messages = signal<ChatMessage[]>([]);
  private readonly _isStreaming = signal<boolean>(false);
  private readonly _currentThought = signal<ThoughtStep | null>(null);
  private readonly _error = signal<string | null>(null);
  private readonly _activeThread = signal<ChatThread | null>(null);

  // --- Exposición Pública Readonly ---
  readonly messages = this._messages.asReadonly();
  readonly isStreaming = this._isStreaming.asReadonly();
  readonly currentThought = this._currentThought.asReadonly();
  readonly error = this._error.asReadonly();
  readonly activeThread = this._activeThread.asReadonly();

  // --- Computed Signals ---
  readonly hasMessages = computed(() => this._messages().length > 0);
  readonly lastMessage = computed(() => this._messages().slice(-1)[0] ?? null);

  /** Envía una consulta al copiloto AI y orquesta el streaming reactivo */
  sendMessage(content: string, cuencaContext?: string): void {
    const text = content.trim();
    if (!text || this._isStreaming()) return;

    this._error.set(null);
    this._isStreaming.set(true);

    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: text,
      timestamp: new Date(),
    };

    const assistantMsgId = crypto.randomUUID();
    const assistantMsg: ChatMessage = {
      id: assistantMsgId,
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      isStreaming: true,
      thoughts: [],
      artifacts: [],
      citations: [],
    };

    this._messages.update((prev) => [...prev, userMsg, assistantMsg]);

    this.streamService.streamAgentMessage(text, cuencaContext).subscribe({
      next: (event) => this.handleStreamEvent(assistantMsgId, event),
      error: (err) => {
        this._error.set(err?.message || 'Error en comunicación con Copiloto');
        this.finishMessageStreaming(assistantMsgId);
      },
      complete: () => {
        this.finishMessageStreaming(assistantMsgId);
      },
    });
  }

  /** Procesa cada evento incremental del stream SSE */
  private handleStreamEvent(assistantId: string, event: AgentStreamEvent): void {
    if (event.tipo === 'chunk' && event.contenido) {
      this._messages.update((list) =>
        list.map((m) => (m.id === assistantId ? { ...m, content: m.content + event.contenido } : m))
      );
    } else if (event.tipo === 'thought' && event.thought) {
      this._currentThought.set(event.thought);
      this._messages.update((list) =>
        list.map((m) =>
          m.id === assistantId ? { ...m, thoughts: [...(m.thoughts || []), event.thought!] } : m
        )
      );
    } else if (event.tipo === 'artifact' && event.artifact) {
      this._messages.update((list) =>
        list.map((m) =>
          m.id === assistantId ? { ...m, artifacts: [...(m.artifacts || []), event.artifact!] } : m
        )
      );
    } else if (event.tipo === 'citation' && event.citation) {
      this._messages.update((list) =>
        list.map((m) =>
          m.id === assistantId ? { ...m, citations: [...(m.citations || []), event.citation!] } : m
        )
      );
    }
  }

  /** Cierra el estado de streaming de un mensaje */
  private finishMessageStreaming(assistantId: string): void {
    this._messages.update((list) =>
      list.map((m) => (m.id === assistantId ? { ...m, isStreaming: false } : m))
    );
    this._isStreaming.set(false);
    this._currentThought.set(null);
  }

  /** Inyecta un widget de Generative UI directamente en la conversación */
  injectArtifact(artifact: DomainArtifact): void {
    const last = this.lastMessage();
    if (last && last.role === 'assistant') {
      this._messages.update((list) =>
        list.map((m) =>
          m.id === last.id ? { ...m, artifacts: [...(m.artifacts || []), artifact] } : m
        )
      );
    } else {
      const msg: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: '',
        timestamp: new Date(),
        artifacts: [artifact],
      };
      this._messages.update((prev) => [...prev, msg]);
    }
  }

  /** Limpia el historial de mensajes actual */
  clearChat(): void {
    this._messages.set([]);
    this._error.set(null);
    this._isStreaming.set(false);
    this._currentThought.set(null);
  }
}
