import { TestBed } from '@angular/core/testing';
import { vi } from 'vitest';
import { ProfilesRepository } from './profiles.repository';
import { SupabaseService } from '@core/services/infrastructure/supabase.service';

// ── Builder del mock de la cadena Supabase ────────────────────────────────────

function buildClientMock(maybeSingleResult: { data: unknown }) {
  return {
    from: vi.fn().mockReturnValue({
      select: vi.fn().mockReturnValue({
        eq: vi.fn().mockReturnValue({
          maybeSingle: vi.fn().mockResolvedValue(maybeSingleResult),
        }),
      }),
    }),
  };
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('ProfilesRepository', () => {
  let repo: ProfilesRepository;
  let clientMock: ReturnType<typeof buildClientMock>;

  beforeEach(() => {
    clientMock = buildClientMock({ data: null });

    TestBed.configureTestingModule({
      providers: [
        { provide: SupabaseService, useValue: { db: clientMock } },
      ],
    });

    repo = TestBed.inject(ProfilesRepository);
  });

  it('should be created', () => {
    expect(repo).toBeTruthy();
  });

  describe('findById()', () => {
    it('should query the profiles table with the given userId', async () => {
      await repo.findById('user-123');
      expect(clientMock.from).toHaveBeenCalledWith('profiles');
    });

    it('should select display_name, avatar_url and role columns', async () => {
      await repo.findById('user-123');
      const selectMock = clientMock.from('profiles').select;
      expect(selectMock).toHaveBeenCalledWith('display_name, avatar_url, role');
    });

    it('should filter by the given userId', async () => {
      await repo.findById('user-123');
      const eqMock = clientMock.from('profiles').select('').eq;
      expect(eqMock).toHaveBeenCalledWith('id', 'user-123');
    });

    it('should return the profile data when found', async () => {
      const mockProfile = { display_name: 'Ada Lovelace', avatar_url: null, role: 'member' };
      clientMock = buildClientMock({ data: mockProfile });
      TestBed.overrideProvider(SupabaseService, { useValue: { db: clientMock } });
      repo = TestBed.inject(ProfilesRepository);

      const result = await repo.findById('user-123');
      expect(result).toEqual(mockProfile);
    });

    it('should return null when no profile is found', async () => {
      const result = await repo.findById('unknown-user');
      expect(result).toBeNull();
    });

    it('should return null when the query throws', async () => {
      const brokenClient = {
        from: vi.fn().mockReturnValue({
          select: vi.fn().mockReturnValue({
            eq: vi.fn().mockReturnValue({
              maybeSingle: vi.fn().mockRejectedValue(new Error('DB error')),
            }),
          }),
        }),
      };
      TestBed.overrideProvider(SupabaseService, { useValue: { db: brokenClient } });
      repo = TestBed.inject(ProfilesRepository);

      const result = await repo.findById('user-123');
      expect(result).toBeNull();
    });
  });
});
