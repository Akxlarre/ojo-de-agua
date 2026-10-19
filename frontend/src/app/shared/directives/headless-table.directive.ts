import { Directive, Input, Output, EventEmitter, signal, computed } from '@angular/core';

export interface TableState<T> {
  data: T[];
  totalRecords: number;
  loading: boolean;
  sortField: string;
  sortOrder: number;
}

@Directive({
  selector: '[koaHeadlessTable]',
  standalone: true,
  exportAs: 'koaHeadlessTable'
})
export class HeadlessTableDirective<T> {
  // Entradas de configuración inmutables
  @Input({ required: true }) set koaHeadlessTable(data: T[]) {
    this.state.update(s => ({ ...s, data }));
  }
  
  @Input('total') set totalInput(val: number) {
    this.state.update(s => ({ ...s, totalRecords: val }));
  }

  // Evento que la UI emitirá cuando necesite más datos (Paginación/Ordenación)
  @Output() loadData = new EventEmitter<any>();

  // Estado interno basado en Signals (El Cerebro)
  private state = signal<TableState<T>>({
    data: [],
    totalRecords: 0,
    loading: false,
    sortField: '',
    sortOrder: 1
  });

  // Señales públicas para que el HTML (UI Generativa) se enlace fácilmente
  data = computed(() => this.state().data);
  total = computed(() => this.state().totalRecords);
  loading = computed(() => this.state().loading);

  // Método al que la vista llamará cuando cambie la paginación de PrimeNG
  load(event: any) {
    this.state.update(s => ({
      ...s,
      loading: true,
      sortField: event.sortField || s.sortField,
      sortOrder: event.sortOrder || s.sortOrder
    }));
    this.loadData.emit(event);
  }

  // Método público para forzar un refresco
  refresh() {
    this.loadData.emit({
        sortField: this.state().sortField,
        sortOrder: this.state().sortOrder
    });
  }
}
