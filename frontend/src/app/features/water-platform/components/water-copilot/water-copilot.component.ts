import {
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  ViewChild,
  afterNextRender,
  effect,
  inject,
  signal,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { WaterChatFacade } from '@core/facades/water-chat.facade';
import { WaterMapFacade } from '@core/facades/water-map.facade';
import { ChatBubbleComponent } from '@shared/components/chat/chat-bubble/chat-bubble.component';
import { ChatBubbleSkeletonComponent } from '@shared/components/chat/chat-bubble/chat-bubble-skeleton.component';
import { ChatInputComponent } from '@shared/components/chat/chat-input/chat-input.component';
import { CuencaCardComponent } from '@shared/components/water/cuenca-card/cuenca-card.component';
import { ProrrateoSimulatorComponent } from '@shared/components/water/prorrateo-simulator/prorrateo-simulator.component';
import { IconComponent } from '@shared/components/icon/icon.component';
import { CardHoverDirective } from '@core/directives/card-hover.directive';
import { SkeletonBlockComponent } from '@shared/components/skeleton-block/skeleton-block.component';
import { DomainArtifact, LegalCitation } from '@core/models/water-chat.model';

@Component({
  selector: 'app-water-copilot',
  standalone: true,
  imports: [
    CommonModule,
    ChatBubbleComponent,
    ChatBubbleSkeletonComponent,
    ChatInputComponent,
    CuencaCardComponent,
    ProrrateoSimulatorComponent,
    IconComponent,
    CardHoverDirective,
    SkeletonBlockComponent,
  ],
  template: `
    <div
      class="flex h-full w-full flex-col rounded-2xl border border-border-default bg-surface shadow-sm overflow-hidden"
    >
      <!-- Header con Selector de Pestañas -->
      <div
        class="flex items-center justify-between border-b border-border-subtle bg-base/50 px-4 py-2.5 backdrop-blur-sm"
      >
        <div class="flex items-center gap-1 bg-subtle p-0.5 rounded-xl">
          <button
            type="button"
            (click)="activeTab.set('chat')"
            class="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition-all border-0 cursor-pointer"
            [class.bg-surface]="activeTab() === 'chat'"
            [class.text-brand]="activeTab() === 'chat'"
            [class.shadow-sm]="activeTab() === 'chat'"
            [class.text-text-muted]="activeTab() !== 'chat'"
          >
            <span class="indicator-live mr-0.5"></span>
            <app-icon name="message-circle" [size]="14" />
            <span>Copiloto AI</span>
          </button>

          <button
            type="button"
            (click)="activeTab.set('ficha')"
            class="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition-all border-0 cursor-pointer"
            [class.bg-surface]="activeTab() === 'ficha'"
            [class.text-brand]="activeTab() === 'ficha'"
            [class.shadow-sm]="activeTab() === 'ficha'"
            [class.text-text-muted]="activeTab() !== 'ficha'"
          >
            <app-icon name="bar-chart-2" [size]="14" />
            <span>Ficha 360° Cuenca</span>
            @if (mapFacade.hasSelectedCuenca()) {
              <span class="h-1.5 w-1.5 rounded-full bg-brand"></span>
            }
          </button>
        </div>

        @if (activeTab() === 'chat' && chatFacade.hasMessages()) {
          <button
            type="button"
            (click)="chatFacade.clearChat()"
            class="text-xs text-text-muted hover:text-red-400 flex items-center gap-1 bg-transparent border-0 cursor-pointer"
            title="Limpiar conversación"
          >
            <app-icon name="trash-2" [size]="13" />
            <span>Limpiar</span>
          </button>
        }
      </div>

      <!-- Pestaña 1: Copiloto AI (Chat) -->
      @if (activeTab() === 'chat') {
        <div class="flex flex-1 flex-col justify-between overflow-hidden p-4 gap-3">
          <!-- Historial de Mensajes -->
          <div #scrollContainer class="flex-1 overflow-y-auto pr-1 flex flex-col gap-1">
            @if (!chatFacade.hasMessages()) {
              <div class="flex h-full flex-col items-center justify-center text-center p-6 text-text-muted">
                <div class="flex h-12 w-12 items-center justify-center rounded-2xl bg-brand-muted text-brand mb-3">
                  <app-icon name="message-circle" [size]="24" />
                </div>
                <h4 class="text-sm font-bold text-text-primary m-0 mb-1">
                  Copiloto de Seguridad Hídrica
                </h4>
                <p class="text-xs text-text-secondary max-w-[260px] m-0">
                  Consulta sobre la salud de cuencas, decretos de sequía MOP, relaves cerca de APRs o simula prorrateo con la Ley 21.435.
                </p>
              </div>
            }

            @for (msg of chatFacade.messages(); track msg.id) {
              <app-chat-bubble
                [message]="msg"
                (citationClick)="onCitationClick($event)"
                (artifactAction)="onArtifactAction($event)"
              />
            }

            @if (chatFacade.isStreaming() && (!chatFacade.lastMessage() || chatFacade.lastMessage()!.content === '')) {
              <app-chat-bubble-skeleton />
            }
          </div>

          <!-- Barra de Entrada -->
          <div class="pt-2 border-t border-border-subtle shrink-0">
            <app-chat-input
              [disabled]="chatFacade.isStreaming()"
              (send)="onSendMessage($event)"
            />
          </div>
        </div>
      }

      <!-- Pestaña 2: Ficha 360° Cuenca -->
      @if (activeTab() === 'ficha') {
        <div class="flex-1 overflow-y-auto p-4 flex flex-col gap-4">
          @if (mapFacade.selectedCuenca(); as cuenca) {
            <app-cuenca-card
              [cuenca]="cuenca"
              [diagnostico]="mapFacade.diagnostico()"
              (simular)="onSimularProrrateo($event.codigo_dga)"
            />

            <!-- Simulador Reactivo de Prorrateo Legal (Art. 5 bis & 18) -->
            <app-prorrateo-simulator [cuencaCodigo]="cuenca.codigo_dga" />

            @if (mapFacade.diagnostico(); as diag) {
              <!-- Desglose de Diagnóstico Holístico -->
              <div class="flex flex-col gap-2 rounded-2xl border border-border-default bg-base/60 p-4 shadow-sm">
                <span class="micro-label text-text-muted flex items-center gap-1.5">
                  <app-icon name="activity" [size]="13" class="text-brand" />
                  Diagnóstico Holístico
                </span>
                <p class="text-xs text-text-secondary leading-relaxed m-0">
                  {{ diag.resumen_ejecutivo }}
                </p>
              </div>

              <!-- Cruces Causales de Amenaza (Inspirado en KpiCard de Autoescuela) -->
              <div class="grid grid-cols-2 gap-3 text-xs">
                <div
                  appCardHover
                  class="rounded-2xl border border-red-500/20 bg-red-500/5 p-3.5 flex flex-col gap-1.5 shadow-sm transition-all hover:border-red-500/40"
                >
                  <div class="flex items-center justify-between">
                    <span class="micro-label text-red-400 font-semibold flex items-center gap-1">
                      <app-icon name="alert-triangle" [size]="12" />
                      Relaves
                    </span>
                    <span class="text-[10px] text-text-muted">&lt;20km APR</span>
                  </div>
                  <span class="kpi-value text-2xl text-red-400 font-bold leading-none">
                    {{ diag.alertas_causales.relaves_cerca_apr }}
                  </span>
                  <span class="text-[11px] text-text-secondary">Amenazas a consumo humano</span>
                </div>

                <div
                  appCardHover
                  class="rounded-2xl border border-border-default bg-surface p-3.5 flex flex-col gap-1.5 shadow-sm transition-all hover:border-brand"
                >
                  <div class="flex items-center justify-between">
                    <span class="micro-label text-text-secondary font-semibold flex items-center gap-1">
                      <app-icon name="file-text" [size]="12" />
                      Patentes No Uso
                    </span>
                    <span class="text-[10px] text-text-muted">TGR</span>
                  </div>
                  <span class="kpi-value text-2xl text-text-primary font-bold leading-none">
                    {{ diag.fiscalizacion.total_patentes_no_uso | number }}
                  </span>
                  <span class="text-[11px] text-text-secondary">UTM retenidas por morosidad</span>
                </div>
              </div>

              <!-- Recomendaciones Legales -->
              @if (diag.recomendaciones_politica_publica && diag.recomendaciones_politica_publica.length > 0) {
                <div class="flex flex-col gap-2 rounded-2xl border border-border-subtle bg-base/60 p-3.5 text-xs">
                  <span class="micro-label text-text-muted flex items-center gap-1">
                    <app-icon name="shield" [size]="12" class="text-brand" />
                    Medidas Código de Aguas & Ley 21.435
                  </span>
                  <ul class="m-0 pl-4 list-disc text-text-secondary flex flex-col gap-1.5">
                    @for (rec of diag.recomendaciones_politica_publica; track rec) {
                      <li class="leading-relaxed">{{ rec }}</li>
                    }
                  </ul>
                </div>
              }
            } @else if (mapFacade.loading()) {
              <div class="flex flex-col gap-3 p-2">
                <app-skeleton-block variant="text" width="60%" height="16px" />
                <app-skeleton-block variant="text" width="100%" height="60px" />
                <div class="grid grid-cols-2 gap-3">
                  <app-skeleton-block variant="rect" width="100%" height="70px" />
                  <app-skeleton-block variant="rect" width="100%" height="70px" />
                </div>
              </div>
            }
          } @else {
            <!-- Estado vacío cuando no hay cuenca seleccionada -->
            <div class="flex h-full flex-col items-center justify-center text-center p-6 text-text-muted">
              <app-icon name="map" [size]="28" class="text-brand mb-2" />
              <h4 class="text-sm font-bold text-text-primary m-0 mb-1">
                Ninguna cuenca seleccionada
              </h4>
              <p class="text-xs text-text-secondary max-w-[240px] m-0 mb-4">
                Haz clic en una cuenca del mapa para abrir su radiografía de seguridad hídrica o elige una rápida:
              </p>
              <div class="flex flex-wrap gap-1.5 justify-center">
                @for (c of quickCuencas; track c.codigo) {
                  <button
                    type="button"
                    (click)="mapFacade.selectCuenca(c.codigo)"
                    class="rounded-lg bg-subtle px-2.5 py-1 text-xs text-text-primary hover:text-brand hover:bg-elevated border-0 cursor-pointer"
                  >
                    {{ c.nombre }}
                  </button>
                }
              </div>
            </div>
          }
        </div>
      }
    </div>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class WaterCopilotComponent {
  readonly chatFacade = inject(WaterChatFacade);
  readonly mapFacade = inject(WaterMapFacade);

  @ViewChild('scrollContainer') private scrollContainer?: ElementRef<HTMLDivElement>;

  readonly activeTab = signal<'chat' | 'ficha'>('chat');

  readonly quickCuencas = [
    { codigo: '057', nombre: 'Río Maipo (RM)' },
    { codigo: '047', nombre: 'Río Choapa' },
    { codigo: '054', nombre: 'Río Petorca' },
    { codigo: '073', nombre: 'Río Maule' },
  ];

  constructor() {
    effect(() => {
      const cuenca = this.mapFacade.selectedCuenca();
      if (cuenca) {
        this.activeTab.set('ficha');
      }
    });

    afterNextRender(() => {
      this.scrollToBottom();
    });
  }

  onSendMessage(text: string): void {
    const cuenca = this.mapFacade.selectedCuenca()?.codigo_dga;
    this.chatFacade.sendMessage(text, cuenca);
    this.scrollToBottom();
  }

  onCitationClick(cit: LegalCitation): void {
    const query = `Explícame en detalle qué exige el ${cit.norma} ${cit.articulo}`;
    this.chatFacade.sendMessage(query);
  }

  onArtifactAction(event: { artifact: DomainArtifact; action: string }): void {
    if (event.artifact.cuencaCodigo) {
      this.mapFacade.selectCuenca(event.artifact.cuencaCodigo);
      this.activeTab.set('ficha');
    }
  }

  onSimularProrrateo(cuencaCodigo: string): void {
    this.activeTab.set('chat');
    this.chatFacade.sendMessage(
      `Simula el prorrateo legal para la cuenca ${cuencaCodigo} con un caudal afluente de 5.000 L/s según el Art. 5 bis.`
    );
  }

  private scrollToBottom(): void {
    if (this.scrollContainer) {
      const el = this.scrollContainer.nativeElement;
      el.scrollTop = el.scrollHeight;
    }
  }
}
