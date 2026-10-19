import { TestBed } from '@angular/core/testing';
import { Injectable } from '@angular/core';
import { vi } from 'vitest';
import { BaseFacade } from './base.facade';

// ── Subclase concreta para tests ──────────────────────────────────────────────

@Injectable({ providedIn: 'root' })
class TestFacade extends BaseFacade<string[]> {
  fetchData = vi.fn<[], Promise<string[]>>().mockResolvedValue(['a', 'b', 'c']);
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function setup() {
  TestBed.configureTestingModule({});
  return TestBed.inject(TestFacade);
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('BaseFacade', () => {
  let facade: TestFacade;

  beforeEach(() => {
    facade = setup();
  });

  // Estado inicial
  describe('initial state', () => {
    it('data should be null', () => {
      expect(facade.data()).toBeNull();
    });

    it('isLoading should be false', () => {
      expect(facade.isLoading()).toBe(false);
    });

    it('error should be null', () => {
      expect(facade.error()).toBeNull();
    });

    it('hasData should be false', () => {
      expect(facade.hasData()).toBe(false);
    });
  });

  // Primera carga (con skeleton)
  describe('initialize() — first call', () => {
    it('should set data after successful fetch', async () => {
      await facade.initialize();
      expect(facade.data()).toEqual(['a', 'b', 'c']);
    });

    it('should set hasData to true after fetch', async () => {
      await facade.initialize();
      expect(facade.hasData()).toBe(true);
    });

    it('should set isLoading to false after fetch', async () => {
      await facade.initialize();
      expect(facade.isLoading()).toBe(false);
    });

    it('should set error when fetchData throws', async () => {
      facade.fetchData.mockRejectedValueOnce(new Error('network error'));
      await facade.initialize();
      expect(facade.error()).toBe('network error');
      expect(facade.data()).toBeNull();
    });

    it('should set isLoading to false even on error', async () => {
      facade.fetchData.mockRejectedValueOnce(new Error('fail'));
      await facade.initialize();
      expect(facade.isLoading()).toBe(false);
    });
  });

  // Patrón SWR: segunda llamada
  describe('initialize() — SWR: second call', () => {
    it('should NOT call fetchData with skeleton on re-entry', async () => {
      await facade.initialize(); // primera carga
      facade.fetchData.mockClear();

      // No await — SWR dispara refresh en background
      facade.initialize();
      expect(facade.isLoading()).toBe(false); // nunca pone loading en re-visita
    });

    it('should silently refresh data on re-entry', async () => {
      await facade.initialize();
      facade.fetchData.mockResolvedValueOnce(['x', 'y']);
      await facade.initialize(); // segunda llamada — refresh silencioso
      expect(facade.data()).toEqual(['x', 'y']);
    });

    it('should keep stale data if silent refresh fails', async () => {
      await facade.initialize();
      facade.fetchData.mockRejectedValueOnce(new Error('timeout'));
      await facade.initialize(); // segunda llamada con error
      expect(facade.data()).toEqual(['a', 'b', 'c']); // datos stale intactos
    });
  });

  // reset()
  describe('reset()', () => {
    it('should clear data', async () => {
      await facade.initialize();
      facade.reset();
      expect(facade.data()).toBeNull();
    });

    it('should force a full reload on next initialize()', async () => {
      await facade.initialize();
      facade.reset();
      facade.fetchData.mockClear();
      await facade.initialize();
      expect(facade.fetchData).toHaveBeenCalledTimes(1);
      expect(facade.isLoading()).toBe(false);
    });
  });

  // retryLoad()
  describe('retryLoad()', () => {
    it('should reset and reload after an error', async () => {
      facade.fetchData.mockRejectedValueOnce(new Error('fail'));
      await facade.initialize();
      expect(facade.error()).not.toBeNull();

      await facade.retryLoad();
      expect(facade.data()).toEqual(['a', 'b', 'c']);
      expect(facade.error()).toBeNull();
    });

    it('should show skeleton on retry (not SWR path)', async () => {
      facade.fetchData.mockRejectedValueOnce(new Error('fail'));
      await facade.initialize();

      // retryLoad llama reset() → _initialized = false → próximo initialize muestra skeleton
      facade.fetchData.mockResolvedValueOnce(['new']);
      await facade.retryLoad();
      expect(facade.data()).toEqual(['new']);
      expect(facade.isLoading()).toBe(false);
    });
  });

  // dispose() — hook para Realtime
  describe('dispose()', () => {
    it('should be callable without error (default no-op)', () => {
      expect(() => facade.dispose()).not.toThrow();
    });
  });
});
