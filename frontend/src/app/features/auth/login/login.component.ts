import {
  Component,
  ChangeDetectionStrategy,
  inject,
  signal,
} from "@angular/core";
import { FormsModule } from "@angular/forms";
import { Router } from "@angular/router";
import { AuthFacade } from "@core/facades/auth.facade";
import { validateEmail } from "@core/utils";

// SEC-T01: Client-side constraints — validated BEFORE calling the auth API
// to prevent unnecessary network calls and provide instant feedback.
const PASSWORD_MIN_LENGTH = 8;
const DISPLAY_NAME_MAX_LENGTH = 100;

// SEC-T05: Map raw Supabase/network error messages to user-safe strings.
// Prevents leaking internal API details (table names, query hints, stack traces).
function sanitizeAuthError(rawMessage: string): string {
  const msg = (rawMessage ?? "").toLowerCase();
  if (msg.includes("invalid login credentials") || msg.includes("invalid credentials"))
    return "Correo o contraseña incorrectos.";
  if (msg.includes("email not confirmed"))
    return "Confirma tu correo antes de iniciar sesión.";
  if (msg.includes("user already registered") || msg.includes("already been registered"))
    return "Ya existe una cuenta con ese correo.";
  if (msg.includes("password should be") || msg.includes("password is too short"))
    return `La contraseña debe tener al menos ${PASSWORD_MIN_LENGTH} caracteres.`;
  if (msg.includes("rate limit") || msg.includes("too many requests"))
    return "Demasiados intentos. Espera unos minutos antes de intentar de nuevo.";
  if (msg.includes("network") || msg.includes("fetch"))
    return "Error de conexión. Verifica tu internet e intenta de nuevo.";
  // Generic fallback — never show raw server messages
  return "Ocurrió un error. Intenta de nuevo o contacta a soporte.";
}

/**
 * LoginComponent — Página pública de inicio de sesión.
 *
 * Genérico y reutilizable. Usa design tokens del sistema
 * y AuthFacade para autenticación con Supabase.
 *
 * Modos disponibles: login | register | reset
 */
@Component({
  selector: "app-login",
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule],
  template: `
    <div
      class="flex min-h-[100dvh] flex-col items-center justify-center bg-base bg-[image:var(--gradient-subtle)] p-4"
    >
      <!-- Koa Greeting Section -->
      <div class="mb-12 text-center animate-fade-in-up">
        <h1 class="m-0 mb-4 text-5xl font-black italic tracking-tighter text-text-primary sm:text-7xl">
          ¡Hola, <span class="text-brand">KOA</span>!
        </h1>
        <p class="m-0 text-xl font-medium text-text-muted">
          Plataforma de gestión inteligente
        </p>
      </div>

      <div
        class="w-full max-w-[420px] rounded-xl border border-border-subtle bg-surface p-8 shadow-lg"
      >
        <!-- Logo / Brand -->
        <div class="mb-6 text-center">
          <div
            class="mb-4 inline-flex h-14 w-14 items-center justify-center rounded-lg bg-[var(--gradient-primary)]"
          >
            <span class="text-2xl brightness-[10]">🧠</span>
          </div>
          <h1
            class="m-0 mb-2 font-display text-2xl font-bold text-text-primary"
          >
            @switch (mode()) {
              @case ("register") {
                Crear Cuenta
              }
              @case ("reset") {
                Recuperar Contraseña
              }
              @default {
                Iniciar Sesión
              }
            }
          </h1>
          <p class="m-0 text-sm text-text-muted">
            @switch (mode()) {
              @case ("register") {
                Completa los campos para registrarte
              }
              @case ("reset") {
                Ingresa tu correo para recibir un enlace
              }
              @default {
                Ingresa tus credenciales para continuar
              }
            }
          </p>
        </div>

        <!-- Error message -->
        @if (errorMsg()) {
          <div
            class="mb-4 flex items-center gap-2 rounded-md border border-[var(--state-error-border)] bg-[var(--state-error-bg)] px-4 py-3 text-sm text-error"
            role="alert"
          >
            <span class="error-icon">⚠</span>
            {{ errorMsg() }}
          </div>
        }

        <!-- Success message -->
        @if (successMsg()) {
          <div
            class="mb-4 flex items-center gap-2 rounded-md border border-[var(--state-success-border)] bg-[var(--state-success-bg)] px-4 py-3 text-sm text-success"
            role="status"
          >
            <span class="success-icon">✓</span>
            {{ successMsg() }}
          </div>
        }

        <!-- Form -->
        <form
          class="flex flex-col gap-4"
          (ngSubmit)="onSubmit()"
          data-llm-form="auth-form"
        >
          <!-- Email -->
          <div class="flex flex-col gap-2">
            <label for="email" class="text-sm font-medium text-text-secondary"
              >Correo electrónico</label
            >
            <input
              id="email"
              type="email"
              data-llm-description="User email address for authentication"
              class="w-full box-border rounded-[var(--input-radius)] border border-[var(--input-border-default)] bg-[var(--input-bg)] px-[var(--input-padding-x)] py-[var(--input-padding-y)] font-body text-base text-[var(--input-text)] outline-none transition-[var(--transition-input)] placeholder-[var(--input-placeholder)] focus:border-[var(--input-border-focus)] focus:shadow-[var(--input-shadow-focus-neutral)]"
              placeholder="tu@correo.com"
              [(ngModel)]="email"
              name="email"
              required
              autocomplete="email"
            />
          </div>

          <!-- Password (not in reset mode) -->
          @if (mode() !== "reset") {
            <div class="flex flex-col gap-2">
              <label
                for="password"
                class="text-sm font-medium text-text-secondary"
                >Contraseña</label
              >
              <input
                id="password"
                type="password"
                data-llm-description="User password for authentication"
                class="w-full box-border rounded-[var(--input-radius)] border border-[var(--input-border-default)] bg-[var(--input-bg)] px-[var(--input-padding-x)] py-[var(--input-padding-y)] font-body text-base text-[var(--input-text)] outline-none transition-[var(--transition-input)] placeholder-[var(--input-placeholder)] focus:border-[var(--input-border-focus)] focus:shadow-[var(--input-shadow-focus-neutral)]"
                placeholder="••••••••"
                [(ngModel)]="password"
                name="password"
                required
                autocomplete="current-password"
              />
            </div>
          }

          <!-- Display name (register only) -->
          @if (mode() === "register") {
            <div class="flex flex-col gap-2">
              <label
                for="displayName"
                class="text-sm font-medium text-text-secondary"
                >Nombre para mostrar</label
              >
              <input
                id="displayName"
                type="text"
                data-llm-description="Display name shown on user profile"
                class="w-full box-border rounded-[var(--input-radius)] border border-[var(--input-border-default)] bg-[var(--input-bg)] px-[var(--input-padding-x)] py-[var(--input-padding-y)] font-body text-base text-[var(--input-text)] outline-none transition-[var(--transition-input)] placeholder-[var(--input-placeholder)] focus:border-[var(--input-border-focus)] focus:shadow-[var(--input-shadow-focus-neutral)]"
                placeholder="Tu nombre"
                [(ngModel)]="displayName"
                name="displayName"
                autocomplete="name"
              />
            </div>
          }

          <!-- Submit button -->
          <button
            type="submit"
            data-llm-action="submit-auth-form"
            class="inline-flex w-full cursor-pointer items-center justify-center gap-2 rounded-[var(--btn-primary-radius)] border-none bg-[var(--btn-primary-bg)] px-[var(--btn-primary-padding-x)] py-[var(--btn-primary-padding-y)] font-body text-base font-semibold text-[var(--btn-primary-text)] shadow-[var(--btn-primary-shadow)] transition-[var(--transition-btn)] hover:enabled:bg-[var(--btn-primary-bg-hover)] hover:enabled:shadow-[var(--btn-primary-shadow-hover)] active:enabled:scale-[var(--btn-press-scale-value)] disabled:cursor-not-allowed disabled:opacity-70"
            [disabled]="loading()"
          >
            @if (loading()) {
              <span
                class="inline-block h-4 w-4 animate-spin rounded-full border-2 border-[rgba(255,255,255,0.3)] border-t-current"
              ></span>
            }
            @switch (mode()) {
              @case ("register") {
                Crear Cuenta
              }
              @case ("reset") {
                Enviar Enlace
              }
              @default {
                Iniciar Sesión
              }
            }
          </button>
        </form>

        <!-- Footer links -->
        <div class="mt-6 flex items-center justify-center gap-2">
          @switch (mode()) {
            @case ("login") {
              <button
                class="cursor-pointer border-none bg-transparent p-0 font-body text-sm text-brand transition-[var(--transition-color)] hover:text-brand-hover"
                data-llm-action="switch-to-password-reset-mode"
                (click)="switchMode('reset')"
              >
                ¿Olvidaste tu contraseña?
              </button>
              <span class="text-sm text-text-muted">·</span>
              <button
                class="cursor-pointer border-none bg-transparent p-0 font-body text-sm text-brand transition-[var(--transition-color)] hover:text-brand-hover"
                data-llm-action="switch-to-register-mode"
                (click)="switchMode('register')"
              >
                Crear cuenta
              </button>
            }
            @case ("register") {
              <button
                class="cursor-pointer border-none bg-transparent p-0 font-body text-sm text-brand transition-[var(--transition-color)] hover:text-brand-hover"
                data-llm-action="switch-to-login-mode"
                (click)="switchMode('login')"
              >
                ¿Ya tienes cuenta? Inicia sesión
              </button>
            }
            @case ("reset") {
              <button
                class="cursor-pointer border-none bg-transparent p-0 font-body text-sm text-brand transition-[var(--transition-color)] hover:text-brand-hover"
                data-llm-action="switch-to-login-mode"
                (click)="switchMode('login')"
              >
                Volver a iniciar sesión
              </button>
            }
          }
        </div>
      </div>
    </div>
  `,
  host: { style: "display: contents;" },
})
export class LoginComponent {
  private readonly auth = inject(AuthFacade);
  private readonly router = inject(Router);

  readonly mode = signal<"login" | "register" | "reset">("login");
  readonly loading = signal(false);
  readonly errorMsg = signal("");
  readonly successMsg = signal("");

  email = "";
  password = "";
  displayName = "";

  switchMode(newMode: "login" | "register" | "reset"): void {
    this.mode.set(newMode);
    this.errorMsg.set("");
    this.successMsg.set("");
  }

  async onSubmit(): Promise<void> {
    this.errorMsg.set("");
    this.successMsg.set("");

    // SEC-T01: Client-side validation — fail fast before hitting the network.
    const validationError = this.validate();
    if (validationError) {
      this.errorMsg.set(validationError);
      return;
    }

    this.loading.set(true);

    try {
      switch (this.mode()) {
        case "login": {
          const { error } = await this.auth.login(this.email.trim(), this.password);
          if (error) {
            this.errorMsg.set(sanitizeAuthError(error.message)); // SEC-T05
          } else {
            this.router.navigate(["/app"]);
          }
          break;
        }

        case "register": {
          const { error } = await this.auth.signUp(
            this.email.trim(),
            this.password,
            { data: { display_name: this.displayName.trim() || undefined } },
          );
          if (error) {
            this.errorMsg.set(sanitizeAuthError(error.message)); // SEC-T05
          } else {
            this.successMsg.set(
              "Cuenta creada. Revisa tu correo para confirmar tu registro.",
            );
            this.switchMode("login");
          }
          break;
        }

        case "reset": {
          const { error } = await this.auth.resetPasswordForEmail(this.email.trim());
          if (error) {
            this.errorMsg.set(sanitizeAuthError(error.message)); // SEC-T05
          } else {
            this.successMsg.set(
              "Se envió un enlace de recuperación a tu correo.",
            );
          }
          break;
        }
      }
    } catch {
      this.errorMsg.set("Ocurrió un error inesperado. Intenta de nuevo.");
    } finally {
      this.loading.set(false);
    }
  }

  /** SEC-T01: Validates form fields before any network call. Returns error string or null. */
  private validate(): string | null {
    const email = this.email.trim();
    if (!email) return "El correo es obligatorio.";
    if (!validateEmail(email)) return "El correo no tiene un formato válido.";

    if (this.mode() !== "reset") {
      if (!this.password) return "La contraseña es obligatoria.";
      if (this.password.length < PASSWORD_MIN_LENGTH)
        return `La contraseña debe tener al menos ${PASSWORD_MIN_LENGTH} caracteres.`;
    }

    if (this.mode() === "register") {
      const name = this.displayName.trim();
      if (name.length > DISPLAY_NAME_MAX_LENGTH)
        return `El nombre no puede superar los ${DISPLAY_NAME_MAX_LENGTH} caracteres.`;
    }

    return null;
  }
}
