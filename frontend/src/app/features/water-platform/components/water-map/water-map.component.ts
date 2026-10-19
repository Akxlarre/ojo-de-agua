import {
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  OnDestroy,
  OnInit,
  ViewChild,
  inject,
  output,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';
import { WaterMapFacade } from '@core/facades/water-map.facade';
import { LayerSelectorComponent } from '@shared/components/water/layer-selector/layer-selector.component';

@Component({
  selector: 'app-water-map',
  standalone: true,
  imports: [CommonModule, LayerSelectorComponent],
  template: `
    <div class="relative h-full w-full overflow-hidden rounded-2xl border border-border-default bg-base shadow-sm">
      <!-- Visor Cartográfico Interactivo (Modo Clean Embed) -->
      <iframe
        #mapIframe
        [src]="mapUrl"
        class="h-full w-full border-0"
        title="Mapa de Cuencas Hidrográficas de Chile"
        loading="eager"
      ></iframe>

      <!-- Selector Flotante de Capas (Top-Left) -->
      <div class="absolute left-4 top-4 z-10 w-64 max-w-[calc(100%-2rem)]">
        <app-layer-selector
          [activeLayers]="mapFacade.activeLayers()"
          (toggle)="onToggleLayer($event)"
        />
      </div>

      <!-- Barra Flotante de Alerta de Sequía (Bottom-Left) -->
      <div
        class="absolute bottom-4 left-4 z-10 flex items-center gap-2 rounded-2xl border border-border-default bg-surface/90 px-3.5 py-2 text-xs backdrop-blur-md shadow-md"
      >
        <span class="flex h-2 w-2 rounded-full bg-red-500 animate-pulse"></span>
        <span class="font-medium text-text-primary">
          {{ mapFacade.cuencasEnSequia().length }} Cuencas en Decreto de Sequía (Art. 314 MOP)
        </span>
      </div>
    </div>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class WaterMapComponent implements OnInit, OnDestroy {
  readonly mapFacade = inject(WaterMapFacade);
  private readonly sanitizer = inject(DomSanitizer);

  @ViewChild('mapIframe') mapIframe?: ElementRef<HTMLIFrameElement>;

  readonly cuencaSelected = output<string>();

  mapUrl: SafeResourceUrl = this.sanitizer.bypassSecurityTrustResourceUrl(
    `/mapa?embed=true&t=${Date.now()}`
  );

  private readonly messageHandler = (event: MessageEvent): void => {
    if (!event.data || typeof event.data !== 'object') return;
    if (event.data.type === 'CUENCA_SELECTED') {
      const codigo = event.data.cuencaCodigo;
      if (codigo) {
        this.mapFacade.selectCuenca(codigo);
        this.cuencaSelected.emit(codigo);
      }
    }
  };

  ngOnInit(): void {
    if (this.mapFacade.cuencas().length === 0) {
      this.mapFacade.loadCuencas();
    }
    window.addEventListener('message', this.messageHandler);
  }

  ngOnDestroy(): void {
    window.removeEventListener('message', this.messageHandler);
  }

  onToggleLayer(layerId: string): void {
    this.mapFacade.toggleLayer(layerId);
    const isVisible = this.mapFacade.isLayerActive(layerId);
    this.sendToMap({
      type: 'TOGGLE_LAYER',
      layerId,
      visible: isVisible,
    });
  }

  private sendToMap(payload: any): void {
    try {
      if (this.mapIframe?.nativeElement?.contentWindow) {
        this.mapIframe.nativeElement.contentWindow.postMessage(payload, '*');
      }
    } catch (e) {
      console.warn('Error al comunicar con visor cartográfico:', e);
    }
  }
}
