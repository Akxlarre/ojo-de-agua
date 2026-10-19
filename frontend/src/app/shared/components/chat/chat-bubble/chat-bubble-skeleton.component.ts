import { ChangeDetectionStrategy, Component } from '@angular/core';
import { SkeletonBlockComponent } from '@shared/components/skeleton-block/skeleton-block.component';

@Component({
  selector: 'app-chat-bubble-skeleton',
  standalone: true,
  imports: [SkeletonBlockComponent],
  template: `
    <div class="flex flex-col gap-2 w-full py-2 items-start" aria-hidden="true">
      <div class="flex items-center gap-2 px-1">
        <app-skeleton-block variant="circle" width="12px" height="12px" />
        <app-skeleton-block variant="text" width="80px" height="12px" />
      </div>

      <div class="w-[75%] rounded-2xl border border-border-default bg-surface p-3.5 flex flex-col gap-2">
        <app-skeleton-block variant="text" width="90%" height="14px" />
        <app-skeleton-block variant="text" width="70%" height="14px" />
        <app-skeleton-block variant="text" width="40%" height="14px" />
      </div>
    </div>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ChatBubbleSkeletonComponent {}
