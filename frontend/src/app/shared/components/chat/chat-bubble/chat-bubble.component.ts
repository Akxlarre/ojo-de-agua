import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ChatMessage, DomainArtifact, LegalCitation } from '@core/models/water-chat.model';
import { IconComponent } from '@shared/components/icon/icon.component';
import { ChatThoughtComponent } from '../chat-thought/chat-thought.component';
import { CardHoverDirective } from '@core/directives/card-hover.directive';

@Component({
  selector: 'app-chat-bubble',
  standalone: true,
  imports: [CommonModule, IconComponent, ChatThoughtComponent, CardHoverDirective],
  template: `
    <div
      class="flex flex-col gap-2 w-full py-2"
      [class.items-end]="message().role === 'user'"
      [class.items-start]="message().role === 'assistant'"
    >
      <!-- Encabezado del emisor -->
      <div class="flex items-center gap-1.5 px-1 text-xs text-text-muted">
        @if (message().role === 'user') {
          <span class="font-medium text-text-secondary">Tú</span>
          <app-icon name="user" [size]="12" />
        } @else {
          <span class="indicator-live mr-0.5"></span>
          <span class="font-semibold text-brand">Copiloto Hídrico</span>
        }
        <span>• {{ message().timestamp | date: 'HH:mm' }}</span>
      </div>

      <!-- Pasos de razonamiento colapsables (Chain of Thought) -->
      @if (message().role === 'assistant' && message().thoughts && message().thoughts!.length > 0) {
        <app-chat-thought [thoughts]="message().thoughts!" />
      }

      <!-- Cuerpo del mensaje -->
      <div
        class="max-w-[88%] rounded-2xl p-3.5 text-sm leading-relaxed"
        [class.bg-brand]="message().role === 'user'"
        [class.text-white]="message().role === 'user'"
        [class.bg-surface]="message().role === 'assistant'"
        [class.text-text-primary]="message().role === 'assistant'"
        [class.border]="message().role === 'assistant'"
        [class.border-border-default]="message().role === 'assistant'"
        [class.shadow-sm]="message().role === 'assistant'"
      >
        <div class="whitespace-pre-wrap select-text">
          {{ message().content }}
        </div>

        @if (message().isStreaming && !message().content) {
          <div class="flex items-center gap-1.5 py-1 text-xs text-text-muted">
            <span class="h-1.5 w-1.5 rounded-full bg-brand animate-ping"></span>
            <span>Consultando el Código de Aguas y Red BNA...</span>
          </div>
        }
      </div>

      <!-- Artefactos Vivos (Generative UI) -->
      @if (message().artifacts && message().artifacts!.length > 0) {
        <div class="flex flex-col gap-2.5 w-full max-w-[88%] mt-1">
          @for (artifact of message().artifacts; track artifact.id) {
            <div
              appCardHover
              class="rounded-2xl border border-brand/30 bg-surface/90 p-4 shadow-sm backdrop-blur-md transition-all hover:border-brand"
            >
              <div class="flex items-center justify-between pb-2 border-b border-border-subtle">
                <span class="micro-label text-brand font-bold">
                  {{ artifact.titulo }}
                </span>
                @if (artifact.subtitulo) {
                  <span class="text-[11px] text-text-muted font-medium">{{ artifact.subtitulo }}</span>
                }
              </div>

              @if (artifact.tipo === 'apr_threat_alert') {
                <div class="py-2.5 text-xs text-text-secondary flex items-start gap-2.5">
                  <app-icon name="alert-triangle" [size]="16" class="text-red-400 shrink-0 mt-0.5" />
                  <div class="leading-relaxed">
                    Alerta de proximidad: Depósitos de relave identificados aguas arriba a menos de 20 km del pozo de captación de agua potable.
                  </div>
                </div>
              }

              @if (artifact.tipo === 'cuenca_kpi' && artifact.datosDiagnostico) {
                <div class="py-2.5 grid grid-cols-2 gap-2 text-xs">
                  <div class="bg-base/70 border border-border-subtle p-2.5 rounded-xl flex flex-col gap-0.5">
                    <span class="micro-label text-text-muted">ISH General</span>
                    <span class="font-bold text-base text-brand leading-none">
                      {{ artifact.datosDiagnostico.indice_seguridad_hidrica }}/100
                    </span>
                  </div>
                  <div class="bg-base/70 border border-border-subtle p-2.5 rounded-xl flex flex-col gap-0.5">
                    <span class="micro-label text-text-muted">Sequía Oficial</span>
                    <span
                      class="font-bold text-base leading-none"
                      [class.text-red-400]="artifact.datosDiagnostico.decreto_escasez_activo"
                      [class.text-emerald-500]="!artifact.datosDiagnostico.decreto_escasez_activo"
                    >
                      {{ artifact.datosDiagnostico.decreto_escasez_activo ? 'VIGENTE' : 'Sin Decreto' }}
                    </span>
                  </div>
                </div>
              }

              <div class="pt-1.5 flex justify-end border-t border-border-subtle">
                <button
                  type="button"
                  (click)="onArtifactAction(artifact, 'view_details')"
                  class="text-xs font-semibold text-brand hover:text-brand-hover flex items-center gap-1 bg-transparent border-0 cursor-pointer p-0"
                >
                  <span>Ver Ficha 360°</span>
                  <app-icon name="chevron-right" [size]="13" />
                </button>
              </div>
            </div>
          }
        </div>
      }

      <!-- Citas Legales Formales -->
      @if (message().citations && message().citations!.length > 0) {
        <div class="flex flex-wrap gap-1.5 max-w-[88%] mt-0.5">
          @for (cit of message().citations; track cit.id) {
            <button
              type="button"
              (click)="onCitationClick(cit)"
              class="inline-flex items-center gap-1.5 rounded-full bg-surface border border-border-default px-2.5 py-1 text-[11px] font-medium text-text-secondary hover:text-brand hover:border-brand shadow-xs transition-all cursor-pointer"
            >
              <app-icon name="file-text" [size]="11" class="text-brand" />
              <span>{{ cit.norma }} · {{ cit.articulo }}</span>
            </button>
          }
        </div>
      }
    </div>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ChatBubbleComponent {
  readonly message = input.required<ChatMessage>();

  readonly citationClick = output<LegalCitation>();
  readonly artifactAction = output<{ artifact: DomainArtifact; action: string }>();

  onCitationClick(cit: LegalCitation): void {
    this.citationClick.emit(cit);
  }

  onArtifactAction(artifact: DomainArtifact, action: string): void {
    this.artifactAction.emit({ artifact, action });
  }
}
