import { TestBed } from '@angular/core/testing';
import { WaterAiStreamService } from './water-ai-stream.service';

describe('WaterAiStreamService', () => {
  let service: WaterAiStreamService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [WaterAiStreamService],
    });
    service = TestBed.inject(WaterAiStreamService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('streamAgentMessage returns an observable', () => {
    const stream$ = service.streamAgentMessage('Hola');
    expect(stream$).toBeTruthy();
  });
});
