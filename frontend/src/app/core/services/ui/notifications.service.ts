import { Injectable, computed, signal } from '@angular/core';

import type { Notification } from '@core/models/notification.model';

/**
 * NotificationsService — estado de notificaciones en memoria (starter).
 *
 * Stub mínimo que alimenta el botón de campana del Topbar. Expone estado vía
 * Signals (sin RxJS) para lectura directa en templates OnPush. Reemplázalo por
 * una facade conectada a Supabase/Realtime cuando el proyecto lo requiera
 * (ver patrón Facade en `.claude/rules/facades.md`).
 */
@Injectable({ providedIn: 'root' })
export class NotificationsService {
  private readonly _notifications = signal<Notification[]>([]);

  /** Lista reactiva de notificaciones (orden: más recientes primero). */
  readonly notifications = this._notifications.asReadonly();

  /** Cantidad de notificaciones sin leer. */
  readonly unreadCount = computed(
    () => this._notifications().filter((n) => !n.read).length,
  );

  /** Reemplaza la lista completa (ej. al cargar desde el backend). */
  setAll(notifications: Notification[]): void {
    this._notifications.set(notifications);
  }

  /** Agrega una notificación al inicio de la lista. */
  add(notification: Notification): void {
    this._notifications.update((list) => [notification, ...list]);
  }

  /** Marca una notificación como leída por id. */
  markRead(id: string): void {
    this._notifications.update((list) =>
      list.map((n) => (n.id === id ? { ...n, read: true } : n)),
    );
  }

  /** Marca todas las notificaciones como leídas. */
  markAllRead(): void {
    this._notifications.update((list) =>
      list.map((n) => ({ ...n, read: true })),
    );
  }
}
