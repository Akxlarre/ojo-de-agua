import { ChangeDetectionStrategy, Component } from '@angular/core';
import { SkeletonBlockComponent } from '@shared/components/skeleton-block/skeleton-block.component';

@Component({
  selector: 'app-cuenca-card-skeleton',
  standalone: true,
  imports: [SkeletonBlockComponent],
  template: `
    <div
      class="flex flex-col gap-3 rounded-xl border border-border-default bg-surface p-4 shadow-sm"
      aria-hidden="true"
    >
      <div class="flex items-center justify-between">
        <app-skeleton-block variant="rect" width="60px" height="20px" />
        <app-skeleton-block variant="rect" width="80px" height="20px" />
      </div>

      <div class="flex flex-col gap-1.5">
        <app-skeleton-block variant="text" width="70%" height="18px" />
        <app-skeleton-block variant="text" width="40%" height="12px" />
      </div>

      <app-skeleton-block variant="rect" width="100%" height="45px" />

      <div class="flex items-center justify-between pt-1 border-t border-border-subtle">
        <app-skeleton-block variant="text" width="60px" height="14px" />
        <app-skeleton-block variant="text" width="50px" height="14px" />
      </div>
    </div>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CuencaCardSkeletonComponent {}
