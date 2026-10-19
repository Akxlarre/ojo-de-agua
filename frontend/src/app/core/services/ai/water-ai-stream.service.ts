import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { AgentStreamEvent } from '@core/models/water-chat.model';
import { environment } from '../../../../environments/environment';

@Injectable({
  providedIn: 'root',
})
export class WaterAiStreamService {
  private readonly baseUrl = environment.apiBaseUrl || 'http://localhost:8000';

  /**
   * Conecta con el endpoint SSE `/api/chat/stream` y emite eventos en tiempo real:
   * pensamientos del agente, chunks de texto, artefactos Generative UI y citas legales.
   */
  streamAgentMessage(consulta: string, cuencaContexto?: string): Observable<AgentStreamEvent> {
    return new Observable<AgentStreamEvent>((observer) => {
      const controller = new AbortController();
      const signal = controller.signal;

      const payload = {
        consulta,
        cuenca_contexto: cuencaContexto || null,
      };

      fetch(`${this.baseUrl}/api/chat/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'text/event-stream',
        },
        body: JSON.stringify(payload),
        signal,
      })
        .then(async (response) => {
          if (!response.ok) {
            throw new Error(`Error en servidor AI: ${response.status} ${response.statusText}`);
          }
          if (!response.body) {
            throw new Error('No se recibió cuerpo de respuesta en el stream.');
          }

          const reader = response.body.getReader();
          const decoder = new TextDecoder('utf-8');
          let buffer = '';

          try {
            while (true) {
              const { done, value } = await reader.read();
              if (done) break;

              buffer += decoder.decode(value, { stream: true });
              const lines = buffer.split('\n');
              buffer = lines.pop() || '';

              for (const line of lines) {
                const trimmed = line.trim();
                if (trimmed.startsWith('data:')) {
                  const jsonStr = trimmed.replace(/^data:\s*/, '');
                  if (jsonStr === '[DONE]') {
                    observer.next({ tipo: 'done' });
                    observer.complete();
                    return;
                  }
                  try {
                    const eventData: AgentStreamEvent = JSON.parse(jsonStr);
                    observer.next(eventData);
                    if (eventData.tipo === 'done') {
                      observer.complete();
                      return;
                    }
                  } catch {
                    // Si no es JSON, se emite como fragmento de texto estándar
                    observer.next({ tipo: 'chunk', contenido: jsonStr });
                  }
                }
              }
            }
            observer.complete();
          } catch (err: any) {
            if (err.name !== 'AbortError') {
              observer.error(err);
            }
          }
        })
        .catch((err) => {
          if (err.name !== 'AbortError') {
            observer.error(err);
          }
        });

      return () => {
        controller.abort();
      };
    });
  }
}
