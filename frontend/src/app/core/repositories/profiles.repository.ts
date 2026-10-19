import { Injectable, inject } from '@angular/core';
import { SupabaseService } from '@core/services/infrastructure/supabase.service';

/**
 * Fila de la tabla `profiles` devuelta por Supabase.
 * Extiende o importa desde `core/models/supabase.types.ts` cuando uses
 * el generador `npm run supabase:types`.
 */
export interface ProfileRow {
  display_name: string | null;
  avatar_url:   string | null;
  role:         string | null;
}

/**
 * ProfilesRepository — acceso tipado a la tabla `profiles`.
 *
 * Es el ÚNICO lugar donde se llama `.db.from('profiles')`.
 * Los Facades de dominio inyectan este repository en vez de SupabaseService directamente.
 *
 * Regla: un método por query. Retorna datos tipados o null (nunca el objeto Supabase raw).
 */
@Injectable({ providedIn: 'root' })
export class ProfilesRepository {
  private client = inject(SupabaseService).db;

  /**
   * Obtiene el perfil de un usuario por su ID.
   * Retorna null si no existe o si ocurre un error de BD.
   */
  async findById(userId: string): Promise<ProfileRow | null> {
    try {
      const { data } = await this.client
        .from('profiles')
        .select('display_name, avatar_url, role')
        .eq('id', userId)
        .maybeSingle();
      return data ?? null;
    } catch {
      return null;
    }
  }
}
