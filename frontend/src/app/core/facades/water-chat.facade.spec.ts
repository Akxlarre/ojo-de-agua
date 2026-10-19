import { TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';
import { WaterChatFacade } from './water-chat.facade';
import { WaterAiStreamService } from '@core/services/ai/water-ai-stream.service';
import { AgentStreamEvent, DomainArtifact } from '@core/models/water-chat.model';

describe('WaterChatFacade', () => {
  let facade: WaterChatFacade;
  let streamServiceMock: jasmine.SpyObj<WaterAiStreamService>;

  beforeEach(() => {
    streamServiceMock = jasmine.createSpyObj<WaterAiStreamService>('WaterAiStreamService', [
      'streamAgentMessage',
    ]);

    TestBed.configureTestingModule({
      providers: [
        WaterChatFacade,
        { provide: WaterAiStreamService, useValue: streamServiceMock },
      ],
    });

    facade = TestBed.inject(WaterChatFacade);
  });

  it('should be created and have empty initial state', () => {
    expect(facade).toBeTruthy();
    expect(facade.messages().length).toBe(0);
    expect(facade.isStreaming()).toBeFalse();
    expect(facade.hasMessages()).toBeFalse();
  });

  it('sendMessage should add user message and handle assistant stream events', () => {
    const mockEvents: AgentStreamEvent[] = [
      { tipo: 'thought', thought: { id: 'T1', pasoNumero: 1, titulo: 'Analizando cuenca...' } },
      { tipo: 'chunk', contenido: 'La Cuenca del Maipo' },
      { tipo: 'chunk', contenido: ' tiene decreto activo.' },
      { tipo: 'done' },
    ];
    streamServiceMock.streamAgentMessage.and.returnValue(of(...mockEvents));

    facade.sendMessage('¿Cómo está el Maipo?');

    expect(facade.messages().length).toBe(2);
    expect(facade.messages()[0].role).toBe('user');
    expect(facade.messages()[0].content).toBe('¿Cómo está el Maipo?');
    expect(facade.messages()[1].role).toBe('assistant');
    expect(facade.messages()[1].content).toBe('La Cuenca del Maipo tiene decreto activo.');
    expect(facade.messages()[1].thoughts?.length).toBe(1);
    expect(facade.isStreaming()).toBeFalse();
  });

  it('handles stream error properly', () => {
    streamServiceMock.streamAgentMessage.and.returnValue(throwError(() => new Error('Stream failed')));

    facade.sendMessage('Consulta fallida');

    expect(facade.error()).toBe('Stream failed');
    expect(facade.isStreaming()).toBeFalse();
  });

  it('clearChat should reset messages and state', () => {
    streamServiceMock.streamAgentMessage.and.returnValue(of({ tipo: 'done' }));
    facade.sendMessage('Hola');
    expect(facade.hasMessages()).toBeTrue();

    facade.clearChat();
    expect(facade.messages().length).toBe(0);
    expect(facade.hasMessages()).toBeFalse();
  });

  it('injectArtifact adds artifact to the latest assistant message or creates one', () => {
    const artifact: DomainArtifact = {
      id: 'A1',
      tipo: 'apr_threat_alert',
      titulo: 'Alerta Relaves APR',
    };

    facade.injectArtifact(artifact);
    const msgs = facade.messages();
    expect(msgs.length).toBe(1);
    expect(msgs[0].artifacts?.length).toBe(1);
    expect(msgs[0].artifacts?.[0].titulo).toBe('Alerta Relaves APR');
  });
});
