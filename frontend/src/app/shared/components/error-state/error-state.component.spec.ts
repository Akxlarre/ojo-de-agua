import { TestBed } from '@angular/core/testing';
import { Component } from '@angular/core';
import { vi } from 'vitest';
import { ErrorStateComponent } from './error-state.component';

// Host stub para testear inputs y outputs
@Component({
  standalone: true,
  imports: [ErrorStateComponent],
  template: `
    <app-error-state
      [title]="title"
      [message]="message"
      [retryLabel]="retryLabel"
      (retry)="onRetry()"
    />
  `,
})
class HostComponent {
  title     = 'Error al cargar';
  message   = 'Network timeout';
  retryLabel = 'Intentar de nuevo';
  onRetry   = vi.fn();
}

describe('ErrorStateComponent', () => {
  it('should be created', () => {
    TestBed.configureTestingModule({ imports: [ErrorStateComponent] });
    const fixture = TestBed.createComponent(ErrorStateComponent);
    fixture.componentRef.setInput('message', 'Error de prueba');
    fixture.detectChanges();
    expect(fixture.componentInstance).toBeTruthy();
  });

  it('should render the message', () => {
    TestBed.configureTestingModule({ imports: [ErrorStateComponent] });
    const fixture = TestBed.createComponent(ErrorStateComponent);
    fixture.componentRef.setInput('message', 'Fallo de red');
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Fallo de red');
  });

  it('should use default title when not provided', () => {
    TestBed.configureTestingModule({ imports: [ErrorStateComponent] });
    const fixture = TestBed.createComponent(ErrorStateComponent);
    fixture.componentRef.setInput('message', 'Error');
    fixture.detectChanges();
    expect(fixture.componentInstance.title()).toBe('No se pudo cargar la información');
  });

  it('should emit retry when action is triggered', () => {
    TestBed.configureTestingModule({ imports: [HostComponent] });
    const fixture = TestBed.createComponent(HostComponent);
    fixture.detectChanges();

    // Simula clic en el botón de acción del alert-card
    const btn = fixture.nativeElement.querySelector('button');
    btn?.click();
    fixture.detectChanges();

    expect(fixture.componentInstance.onRetry).toHaveBeenCalledTimes(1);
  });
});
